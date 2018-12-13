"""
Plot a stat over another stat.

Example:
    python plot.py --inputfolder simData/numMotes_50/ -x chargeConsumed --y aveLatency
"""

# =========================== imports =========================================

# standard
import os
import argparse
import json
import glob
from collections import OrderedDict
import numpy as np

# third party
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json
import io
import re
import numpy as np
import operator
from functools import reduce
# ============================ defines ========================================

KPIS = [
    'latency_max_s',
    'latency_avg_s',
    'latencies',
    'lifetime_AA_years',
    'sync_time_s',
    'join_time_s',
    'upstream_num_lost',
    'upstream_reliability'
]

# ============================ main ===========================================

def main(options):

    # init
    data = OrderedDict()

    # chose lastest results
    subfolders = list(
        map(lambda x: os.path.join(options.inputfolder, x),
            os.listdir(options.inputfolder)
        )
    )
    subfolder = max(subfolders, key=os.path.getmtime)

    # Make it work for Python 2+3 and with Unicode
    try:
        to_unicode = unicode
    except NameError:
        to_unicode = str

    for key in options.kpis:
        # load data
        for file_path in sorted(glob.glob(os.path.join(subfolder, '*.kpi'))):
            curr_combination = os.path.basename(file_path)[:-8] # remove .dat.kpi
            with open(file_path, 'r') as f:
           
                # read kpi file
                kpis = json.load(f)

                # init data list
                data[curr_combination] = []

                # fill data list
                for run in kpis.itervalues():
                    for mote in run.itervalues():
                        if key in mote:
                            data[curr_combination].append(mote[key])

        # plot
        try:
            if key in ['lifetime_AA_years','latencies']:
                plot_cdf(data, key, subfolder)

            else:
                if key in ['upstream_reliability']:
                    #save data in another file mote 0,1,2,3
                    print("KEYYY" + str(key))
                    pdr_data = data.values()[0]
                    print("pppppppddddddddddddddrrrrrrrrrrrrrrrrrrrrrrrr:: " + str(data))
                    save_pdrs(pdr_data,subfolder)
                    #plot_box(datas, key, subfolder)
                else:
                    plot_box(data, key, subfolder)



        except TypeError as e:
            print "Cannot create a plot for {0}: {1}.".format(key, e)
    print "Plots are saved in the {0} folder.".format(subfolder)

# =========================== helpers =========================================

def plot_cdf(data, key, subfolder):
    for k, values in data.iteritems():
        # convert list of list to list
        if type(values[0]) == list:
            values = sum(values, [])

        # compute CDF
        sorted_data = np.sort(values)
        yvals = np.arange(len(sorted_data)) / float(len(sorted_data) - 1)
        plt.plot(sorted_data, yvals, label=k)

    plt.xlabel(key)
    plt.ylabel("CDF")
    plt.legend()
    savefig(subfolder, key + ".cdf")
    plt.clf()

def plot_box(data, key, subfolder):
    plt.boxplot(data.values())
    plt.xticks(range(1, len(data) + 1), data.keys())
    plt.ylabel(key)
    savefig(subfolder, key)
    plt.clf()

def  save_pdrs(data,subfolder):
    mote_counter = 1
    print("OS PATH::: "+str(os.path.isfile("./pdrs.json")))
    json_string =  '''{"simulations": []}'''
    json_begin = '{"simulations":['
    json_end = ']}'
    outer_list = []

    if os.path.isfile("./pdrs.json") == False:
        with io.open("pdrs.json", 'w', encoding='utf-8') as feedsjson:
            # convert it to a python dictionary
            json_dict = json.loads(json_string)
            print("json dict::: " + str(json_dict))
            for pdr in data:
                #json_dict['simulations'].append({'mote_id': mote_counter, 'pdr': pdr})
                #json_dict['simulations'].append({'mote_id': mote_counter, 'pdr': pdr})
                json_dict['simulations'].append({'mote_id_'+str(mote_counter): pdr})
                mote_counter += 1
            outer_list.append(json_dict)
            feedsjson.write(json.dumps(json_dict, ensure_ascii=False))
            #feedsjson.write(json.dumps(json_dict, indent=4, sort_keys=True,
              #                         separators=(',', ': '), ensure_ascii=False))
    else:
        #with io.open("pdrs.json", 'a', encoding='utf-8') as commas:

             #commas.write(unicode(','))
        with io.open("pdrs.json", 'a', encoding='utf-8') as feedsjson:
            feedsjson.write(unicode(','))
             # convert it to a python dictionary
            json_dict = json.loads(json_string)
            print("json dict::: "+str(json_dict))
            for pdr in data:
                json_dict['simulations'].append({ 'mote_id_'+str(mote_counter): pdr})
                #json_dict.append({'mote_id': mote_counter, 'pdr': pdr})
                mote_counter += 1
            outer_list.append(json_dict)
            feedsjson.write(json.dumps(json_dict, ensure_ascii=False))
            #feedsjson.write(json.dumps(json_dict, indent = 4, sort_keys = True,
            # separators = ( ',', ': '), ensure_ascii = False))
            #feedsjson.write(unicode(json_end))

    with open('pdrs.json', 'r') as handle:
        text_data = handle.read()
        text_data = '[' + re.sub(r'\}\s\{\[ \{', '},{', text_data) + ']'
        pdr_values = json.loads(text_data)

        all_simulations = {
            k: [d.get(k) for d in pdr_values]
            for k in set().union(*pdr_values)
        }

        motes_data = []

        #motes_data = all_simulations.get(u'simulations')
        for each_list in all_simulations.get(u'simulations'):
            for each_dict in each_list:
                motes_data.append(each_dict)
        #print("FINAL DICT::: " + str(motes_data))

        final_pdrs = {
            k: [d.get(k) for d in motes_data ]
            for k in set().union(*motes_data)
        }

        final_pdrs = {k: filter(bool, v) for k, v in final_pdrs.iteritems()}
        print("ALL SIMULATIONS::: " + str(final_pdrs))

        #plotting results
        index = []
        data = []
        for i, (key, val) in enumerate(final_pdrs.iteritems()):
            index.append(key)
            data.append(map(float, val))

        avg_pdr_per_mote = []
        num_motes = 0
        mote_names = []
        for each_list in data:
            avg_pdr_per_mote.append(sum(each_list) / float(len(each_list)))
            num_motes += 1
            mote_names.append("mote"+str(num_motes))

        print("DATAA::: " + str(avg_pdr_per_mote))

        x = np.arange(num_motes)
        plt.bar(x, height= avg_pdr_per_mote, width = 1.0, edgecolor = 'black')
        plt.xticks(x, mote_names)

        savefig(subfolder, "PDR PER MOTE SINGLE OR MULTI SIMULATIONS")
        plt.clf()


def savefig(output_folder, output_name, output_format="png"):
    # check if output folder exists and create it if not
    if not os.path.isdir(output_folder):
        os.makedirs(output_folder)

    # save the figure
    plt.savefig(
        os.path.join(output_folder, output_name + "." + output_format),
        bbox_inches     = 'tight',
        pad_inches      = 0,
        format          = output_format,
    )

def parse_args():
    # parse options
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--inputfolder',
        help       = 'The simulation result folder.',
        default    = 'simData',
    )
    parser.add_argument(
        '-k','--kpis',
        help       = 'The kpis to plot',
        type       = list,
        default    = KPIS
    )
    parser.add_argument(
        '--xlabel',
        help       = 'The x-axis label',
        type       = str,
        default    = None,
    )
    parser.add_argument(
        '--ylabel',
        help       = 'The y-axis label',
        type       = str,
        default    = None,
    )
    parser.add_argument(
        '--show',
        help       = 'Show the plots.',
        action     = 'store_true',
        default    = None,
    )
    return parser.parse_args()

if __name__ == '__main__':

    options = parse_args()

    main(options)
