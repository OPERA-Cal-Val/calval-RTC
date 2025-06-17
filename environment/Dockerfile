FROM jupyter/base-notebook:lab-4.0.7 AS release

USER root
WORKDIR /
RUN set -ve

RUN apt update
RUN apt install --no-install-recommends -y \
        software-properties-common \
        git && \
    apt-get install -y gpg-agent && \
    add-apt-repository -y ppa:ubuntugis/ubuntugis-unstable && \
    apt update && \
    apt upgrade -y

RUN apt install --no-install-recommends --fix-missing -y \
    zip \
    unzip \
    wget \
    vim \
    rsync \
    less \
    snaphu \
    curl \
    openssh-client \
    libgl1-mesa-glx \
    emacs \
    gnupg2 \
    jq \
    gfortran \
    make \
    proj-bin \
    geotiff-bin \
    libshp-dev \
    libshp2 \
    libhdf5-dev \
    libnetcdf-dev \
    libgdal-dev \
    libgsl-dev \
    gdal-bin \
    ### SNAP
    default-jdk-headless \
    ### Install texlive for PDF exporting of notebooks containing LaTex
    texlive-xetex \
    texlive-fonts-recommended \
    texlive-plain-generic \
    ### PyGMTSAR
    csh \
    autoconf \
    make \ 
    libtiff5-dev \ 
    liblapack-dev \
    libgmt-dev \
    gmt-dcw \
    gmt-gshhg \
    gmt \
    --

RUN mamba install -c conda-forge -y \
    ### Install plotting and general
    awscli \
    boto3 \
    pyyaml \
    bokeh \
    plotly \
    'pyopenssl>=23.0.0' \
    zstd==1.5.5 \
    zstandard==0.21.0 \
    kernda \
    jupyter-resource-usage \
    nb_conda_kernels \
    jupyterlab-spellchecker \
    ipympl \
    jupyterlab_widgets \
    ipywidgets \
    jupyterlab-git \
    panel \
    dask-gateway \
    dask \
    distributed \
    --

RUN python3 -m pip install \
        jupyterlab-jupyterbook-navigation==1.0.4 \
        jupyterlab_myst \
        ### For pyGMTSAR
        pygmtsar &&\
    cd / &&\
        mkdir -p /tmp/build/GMTSAR /usr/local/GMTSAR &&\
        git clone --branch master https://github.com/gmtsar/gmtsar /tmp/build/GMTSAR/ &&\
        cd /tmp/build/GMTSAR &&\
        autoconf &&\
        ./configure --with-orbits-dir=/tmp CFLAGS='-z muldefs' LDFLAGS='-z muldefs' &&\
        make &&\
        make install &&\
        mv -v /tmp/build/GMTSAR/bin /usr/local/GMTSAR/bin &&\
        rm -rf /tmp/build &&\
    cd / &&\

    # Make sure that any files in the home directory are jovyan permission
    chown -R jovyan:users $HOME/ &&\
    # Make sure mamba (within conda) has write access
    chmod -R 777 /opt/conda/pkgs/ &&\
    # Make sure JupyterLab settings is writable
    mkdir -p /opt/conda/share/jupyter/lab/settings/ &&\
    chown jovyan:users /opt/conda/share/jupyter/lab/settings/ &&\
    chmod -R 775 /opt/conda/share/jupyter/lab/settings/ &&\
    # Add sudo group user 599 elevation
    addgroup -gid 599 elevation &&\
    echo '%elevation ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers &&\
    # Use the kernel display name `base` for the base conda environment
    mamba run -n base kernda --display-name base -o /opt/conda/share/jupyter/kernels/python3/kernel.json &&\
    mamba clean -y --all &&\
    mamba init &&\
    rm -rf /home/jovyan/..?* /home/jovyan/.[!.]* /home/jovyan/*

    RUN wget https://raw.githubusercontent.com/OPERA-Cal-Val/calval-RTC/main/environment/pinned_environment.yaml -P /etc/env/ && \
    mamba env create -f /etc/env/pinned_environment.yaml && \
    /opt/conda/envs/opera_calval_rtc/bin/python -m ipykernel install --prefix /opt/conda/envs/opera_calval_rtc --name opera_calval_rtc && \
    mamba clean --yes --all && \
    chmod -R 755 /opt/conda/envs && \
    chown -R jovyan:users /opt/conda/envs

### GMTSAR
ENV PATH=/usr/local/GMTSAR/bin:$PATH

WORKDIR /home/jovyan
USER jovyan
