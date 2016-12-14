from casino import main as casino_main
import json
import numpy
import operator

if __name__ == '__main__':
    
    """
    Things to do so that you can run this script:
    - Return player on the casino main (and comment the print)
    - Comment student.py end() func prints
    """

    j = 0.35
    dic1 = {}
    while j < 0.65:
        dic = {}
        with open('settings.json', 'r') as data_file:    
            configs = json.load(data_file)
        configs['bust_threshold'] = j 
        with open('settings.json', 'w') as data_file:
            json.dump(configs, data_file)
        for i in range(20):
            p = casino_main(n_games=configs['n_tests'], pocket=configs['pocket'])
            dic['win'] = dic.get('win', 0) + p.wins
            dic['defeats'] = dic.get('defeats', 0) + p.defeats
            dic['draws'] = dic.get('draws', 0) + p.draws
            dic['surrenders'] = dic.get('surrenders', 0) + p.surrenders
            dic['passed'] = dic.get('passed', 0) + p.dont_play
        print("*******J = ", j," *********")
        print(numpy.mean(dic['win']))
        print(numpy.mean(dic['defeats']))
        print(numpy.mean(dic['draws']))
        print(numpy.mean(dic['surrenders']))
        print(numpy.mean(dic['passed']))
        dic1[j] = dic['win'] / (dic['win'] + dic['defeats'] + dic['draws'] + dic['surrenders'] + dic['passed'])
        j += 0.05
    print(max(dic1.items(), key=operator.itemgetter(1)))

