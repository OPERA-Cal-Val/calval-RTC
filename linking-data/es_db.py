import concurrent.futures
from functools import lru_cache
from pathlib import Path

import backoff
import requests
import urllib3
from http.client import RemoteDisconnected
from dotenv import dotenv_values
from elasticsearch import Elasticsearch, RequestsHttpConnection
from elasticsearch_dsl import Q, Search
from tqdm import tqdm

urllib3.disable_warnings()

RTC_SAS_VERSION = '1.0.1'
STATIC_INDEX = 'grq_v1.0_l2_rtc_s1_static_layers-2023.09'
RTC_INDEX = 'grq_v1.0_l2_rtc_s1-2023.09'


def download_file(url: str, out_path: str):
    # Source: https://stackoverflow.com/a/16696317
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(out_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=2**6):
                f.write(chunk)
    return out_path


@lru_cache
def get_search_client(index: str = None):
    config = dotenv_values()
    ES_USERNAME = config['ES_USERNAME']
    ES_PASSWORD = config['ES_PASSWORD']
    GRQ_URL = 'https://100.104.62.10/grq_es/'
    # See: https://github.com/nasa/opera-sds-pcm/
    # blob/81ccb1bd40981588754a438b4dd0eb1506301276/tools/ops/cnm_check.py#L40-L47
    grq_client = Elasticsearch(GRQ_URL,
                               http_auth=(ES_USERNAME, ES_PASSWORD),
                               verify_certs=False,
                               use_ssl=True,
                               connection_class=RequestsHttpConnection,
                               read_timeout=50000,
                               terminate_after=2500,
                               ssl_show_warn=False
                               )
    if index is None:
        index = RTC_INDEX
    elif index == 'static':
        index = STATIC_INDEX
    search = Search(using=grq_client,
                    index=index)

    if not grq_client.ping():
        raise ValueError('Either JPL username/password is wrong or not connected to VPN')

    return search


def get_rtc_docs(input_id: str,
                 target_rtc_version=RTC_SAS_VERSION) -> list[dict]:
    "Version is determined by latest here: https://github.com/opera-adt/RTC/releases"
    search = get_search_client()
    q_qs = Q('bool',
             must=[Q('query_string',
                     query=f'\"{input_id}\"',
                     default_field="metadata.input_granule_id"),
                   Q('query_string',
                      query=f'\"{target_rtc_version}\"',
                      default_field="metadata.sas_version")])
    query = search.query(q_qs)
    total = query.count()
    # using this: https://github.com/elastic/elasticsearch-dsl-py/issues/737
    query = query[0:total]
    resp = query.execute()

    hits = list(resp.hits)
    data = [hit.to_dict() for hit in hits]
    return data


@backoff.on_exception(backoff.expo,
                      TimeoutError,
                      max_tries=20,
                      jitter=backoff.full_jitter)
def get_static_rtc_docs(rtc_docs: list[dict],
                        target_rtc_version=RTC_SAS_VERSION) -> list[dict]:
    burst_ids = [doc['metadata']['Files'][0]['burst_id'] for doc in rtc_docs]
    burst_ids = list(set(burst_ids))

    queries = [Q('bool',
                 must=[Q('query_string',
                         query=f'\"OPERA_L2_RTC-S1-STATIC_{burst_id}\"',
                         default_field="metadata.id"),
                       Q('query_string',
                         query=f'\"{target_rtc_version}\"',
                         default_field="metadata.sas_version")
                         ])
                for burst_id in burst_ids]

    @backoff.on_exception(backoff.expo,
                          RemoteDisconnected,
                          max_tries=20,
                          jitter=backoff.full_jitter)
    def _get_static_doc_from_query(input_data):
        search = get_search_client(index='static')
        query_qs, burst_id = input_data
        query = search.query(query_qs)
        total = query.count()
        # using this: https://github.com/elastic/elasticsearch-dsl-py/issues/737
        if total == 0:
            print(f'{burst_id} does not have a entry in ES')
            return {burst_id: {}}
        query = query[0:1]
        resp = query.execute()
        hits = list(resp.hits)
        return {burst_id: hits[0].to_dict()}
    input_data = list(zip(queries, burst_ids))
    # data = list(map(_get_static_doc_from_query, input_data))
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        out_data = list((executor.map(_get_static_doc_from_query, input_data)))
    return out_data


def get_rtc_urls(rtc_docs_lst: list[dict]) -> dict:
    urls = [{rtc_doc['id']: rtc_doc['metadata']['product_urls']
             for rtc_doc in rtc_docs} for rtc_docs in rtc_docs_lst]
    return urls


def _get_dst_paths_for_rtc(product_url_dicts: dict,
                           directory=None) -> list[Path]:
    parent = directory or Path('.')
    out_paths = [parent / Path(opera_id) / url.split('/')[-1]
                 for opera_id, urls in product_url_dicts.items()
                 for url in urls]
    return out_paths


def _get_urls_from_dict(product_url_dicts: dict) -> list[str]:
    urls = [url for _, urls in product_url_dicts.items() for url in urls]
    return urls


def download_rtc_products(url_dict: dict, directory: Path = None) -> Path:
    out_paths = _get_dst_paths_for_rtc(url_dict, directory=directory)
    [path.parent.mkdir(exist_ok=True, parents=True) for path in out_paths]
    urls = _get_urls_from_dict(url_dict)

    def download_one(data):
        url, out_path = data
        download_file(url, out_path)
        return out_path

    data_inputs = list(zip(urls, out_paths))
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        _ = list(tqdm(executor.map(download_one, data_inputs),
                      total=len(data_inputs)))
    return out_paths
