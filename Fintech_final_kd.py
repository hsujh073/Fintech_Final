class Strategy():
    # option setting needed
    def __setitem__(self, key, value):
        self.options[key] = value

    # option setting needed
    def __getitem__(self, key):
        return self.options.get(key, '')

    def __init__(self):
        # strategy property
        self.subscribedBooks = {
            'Binance': {
                'pairs': ['BTC-USDT'],
            },
        }
        self.period = 10 * 60
        self.options = {}

        # user defined class attribute
        self.last_type = 'sell'
        #self.last_cross_status = None
        self.close_price_trace = np.array([])
        self.kd_period = 9
        self.k_value = 50
        self.d_value = 50
        self.buy_value = None
        self.sell_flag = False
        self.time_limit = 50
        self.decay = 0.98
        self.earn_rate = 0.008
        self.ammount = 0

        self.NOEV = 0
        self.UP = 1
        self.DOWN = 2

    def get_current_kd_value(self):
        near_min = talib.MIN(self.close_price_trace, self.kd_period)[-1]
        near_max = talib.MAX(self.close_price_trace, self.kd_period)[-1]
        if np.isnan(near_min) or np.isnan(near_max):
            return None
        RSV = (self.close_price_trace[-1] - near_min) / (near_max - near_min) *100.0
        n_k_value = self.k_value * 2/3 + RSV * 1/3
        n_d_value = self.d_value * 2/3 + self.k_value * 1/3
        if n_k_value < n_d_value and self.k_value > self.d_value:
            now_type = self.UP
        elif n_k_value > n_d_value and self.k_value < self.d_value:
            now_type = self.DOWN
        else:
            now_type = self.NOEV
        self.k_value = n_k_value
        self.d_value = n_d_value
        #Log("k-value: "+str(n_k_value)+" d-value: "+str(n_d_value))
        return now_type


    # called every self.period
    def trade(self, information):

        exchange = list(information['candles'])[0]
        pair = list(information['candles'][exchange])[0]
        close_price = information['candles'][exchange][pair][0]['close']

        # add latest price into trace
        self.close_price_trace = np.append(self.close_price_trace, [float(close_price)])
        # only keep max length of ma_long count elements
        self.close_price_trace = self.close_price_trace[-self.kd_period:]
        # calculate current kd cross status
        cur_kd_cross = self.get_current_kd_value()

        #Log('info: ' + str(information['candles'][exchange][pair][0]['time']) + ', ' + str(information['candles'][exchange][pair][0]['open']) + ', assets' + str(self['assets'][exchange]['BTC']))

        if cur_kd_cross is None:
            return []

        #if self.last_cross_status is None:
        #    self.last_cross_status = cur_kd_cross
        #    return []

        # cross up
        if self.last_type == 'sell' and cur_kd_cross == self.UP:
            self.last_type = 'buy'
            self.buy_value = self.close_price_trace[-1]
            self.ammount = 1
            return [
                {
                    'exchange': exchange,
                    'amount': 1,
                    'price': -1,
                    'type': 'MARKET',
                    'pair': pair,
                }
            ]
        # cross down
        #elif self.last_type == 'buy' and cur_kd_cross == self.DOWN and self.close_price_trace[-1] > self.buy_value:
        elif (self.last_type == 'buy' and self.close_price_trace[-1] > self.buy_value * (1+self.earn_rate)):# or self.time_limit<=0:
            self.last_type = 'sell'
            self.buy_value = None
            self.time_limit = 50
            self.earn_rate = 0.008
            now_ammount = self.ammount
            self.ammount = 0
            return [
                {
                    'exchange': exchange,
                    'amount': -now_ammount,
                    'price': -1,
                    'type': 'MARKET',
                    'pair': pair,
                }
            ]
        elif self.last_type == 'buy':
            self.time_limit = self.time_limit-1
            if self.time_limit <= 0:
                self.earn_rate = 0.002
            else:
                self.earn_rate = self.earn_rate * self.decay
            if self.time_limit < 25 and self.ammount < 5 and self.close_price_trace[-1] < self.buy_value * 0.98:
                self.buy_value = (self.buy_value*self.ammount +self.close_price_trace[-1]) / (self.ammount+1)
                self.ammount = self.ammount+1
                self.time_limit = 50
                self.earn_rate = 0.008
                return [
                    {
                        'exchange': exchange,
                        'amount': 1,
                        'price': -1,
                        'type': 'MARKET',
                        'pair': pair,
                    }
                ]
        return []
