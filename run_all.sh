#!/bin/sh
# Full pipeline (about 1-2 hours on 2 cores). Results are already included in results/.
set -e
mkdir -p libs results work
git clone --depth 1 https://github.com/python-humanize/humanize libs/humanize
git clone --depth 1 https://github.com/more-itertools/more-itertools libs/more-itertools
pip install -e libs/humanize -e libs/more-itertools
python -c "import glob,polib;[polib.pofile(p).save_as_mofile(p[:-3]+'.mo') for p in glob.glob('libs/humanize/src/humanize/locale/*/LC_MESSAGES/*.po')]"
python mutate.py configs/humanize.json 0 2 & python mutate.py configs/humanize.json 1 2 & wait
python mutate.py configs/moreit.json 0 2 & python mutate.py configs/moreit.json 1 2 & wait
cp -r libs/humanize work/base && cp -r libs/more-itertools work/mibase
python recheck_i18n.py && python recheck_unittest.py
python confirm.py random && python confirm.py edges
python analyze.py
