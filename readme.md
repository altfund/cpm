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
# in test mode any transfers and transactions are printed to the console only

python cpm.py
```

In config, percentages are defined as decimals. So 100% is 1, 50% is 0.5, 10% is .1, etc. The leading 0 is optional.

We have no way to track transactions since they have to be cleared on the exchange before we can get any info about them, so the prices/stats that you want will have to be collected and attributed after-the-fact