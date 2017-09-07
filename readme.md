```
virtualenv --python=python3 env
source env/bin/activate

git clone https://github.com/altfund/bitfinex-1
cd bitfinex-1
pip install -r requirements.txt
python setup.py install
cd ..

git clone https://github.com/altfund/bittrex
cd bittrex
pip install -r requirements.txt
python setup.py install
cd ..

git clone https://github.com/altfund/kraken
cd kraken
python setup.py install
cd ..

cp config_template config
# edit your config to contain you api credentials and preferences
# settings.test determines whether actual trades will be made, default test=True

python cpm.py
```