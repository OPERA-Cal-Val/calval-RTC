import subprocess
from pathlib import Path

import papermill as pm

# list of paths to OPERA-RTC mosaics on which to run RLE
stack_dirs = [
    "path/to/dir/holding/RTC/stack",
]

# True to delete mosaicked RTCs and static files, False to save
delete_mosaics = False

output_dirs = [Path(f"{p}/output_RLE/RLE_{Path(p).name}") for p in stack_dirs]

polarizations = ["VV", "VH"]

for i, d in enumerate(stack_dirs):
    for p in polarizations:
        # comment out any file types in cleanup_list that you wish to save
        # uncomment those to delete
        cleanup_list = (
            # f"{p} amplitude data, "
            # f"flattened {p} amplitude data, "
            # f"flattened and tiled {p} amplitude data, "
            # f"{p} tile correlation results, "
            f", "  # don't remove if cleanup list empty
        )

        parameters = {
            "polarization": p,
            "stack_dir": d,
            "delete_mosaics": delete_mosaics,
            "cleanup_list": cleanup_list,
        }
        output_dirs[i].mkdir(exist_ok=True, parents=True)
        output = output_dirs[i] / f"output_{Path(d).name}_{p}_RLE.ipynb"
        output_html = Path(output).with_suffix('.html')
        output_pdf = Path(output).with_suffix('.pdf')
        pm.execute_notebook(
            "RLE.ipynb", output, kernel_name="python3", parameters=parameters
        )

        subprocess.run([f"jupyter nbconvert {output} --to html"], shell=True)
        subprocess.run(
            [f"pandoc {output_html} -o {output_pdf} --pdf-engine=weasyprint"],
            shell=True,
        )

        # Load data
        rle_csv_file = next(output_dirs[i].parent.glob(f'*{p}*.csv'), None)
        df = pd.read_csv(rle_csv_file)

        # Report percentage of scenes that pass
        condition = (df['tile_mean_x'].abs() > 6) | (df['tile_mean_y'].abs() > 6)
        count = condition.sum()
        pass_percentage = 100 - ((count / len(df)) * 100)

        print(f"Percentage of scenes for {p} polarization which pass: {pass_percentage:.2f}%")
