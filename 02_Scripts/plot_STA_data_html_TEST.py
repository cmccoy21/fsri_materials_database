# MCC Data Import and Pre-processing
#   by: Mark McKinnon and Craig Weinschenk
# ***************************** Run Notes ***************************** #
# - Prompts user for directory with MCC raw data                        #
#                                                                       #
# - Imports raw MCC data and creates excel sheets with header           #
#       information, raw data, and analyzed data (baseline and          #
#       mass loss corrected)                                            #
#                                                                       #
# ********************************************************************* #

# --------------- #
# Import Packages #
# --------------- #
import os
import glob
import numpy as np
import pandas as pd
import math
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
import plotly.graph_objects as go
import git
import ruptures as rpt

label_size = 20
tick_size = 18
line_width = 2
legend_font = 10
fig_width = 10
fig_height = 6

def apply_savgol_filter(raw_data, deriv=0):

    window_raw = int((raw_data.count())/40)
    window = int(np.ceil(window_raw) // 2 * 2 + 1)

    if window < 6:
        poly_order = 3
    else:
        poly_order = 5

    raw_data = raw_data.dropna().loc[0:]
    converted_data = savgol_filter(raw_data,window,poly_order, deriv=deriv)
    filtered_data = pd.Series(converted_data, index=raw_data.index.values)
    return(filtered_data.loc[0:])

def clean_file(file_name):
    fin = open(file_name, 'rt', encoding = 'UTF-16')
    fout = open(f'{file_name}_TEMP.tst', 'wt', encoding = 'UTF-16')
    #output file to write the result to
    for line in fin:
        #read replace the string and write to output file
        fout.write(line.replace('\t\t', '\t'))
    #close input and output files
    fin.close()
    fout.close()

def search_string_in_file(file_name, string_to_search):
    line_number = 0
    list_of_results = []
    with open(file_name, 'r', encoding='UTF-16') as read_obj:
        for line in read_obj:
            line_number += 1
            if string_to_search in line:
                line_num = line_number
    return line_num

def unique(list1):
 
    unique_list = []
     
    for x in list1:
        if x not in unique_list:
            unique_list.append(x)

    return unique_list

def plot_mean_data(df):

    hr_dict = {'3K_min':'red', '10K_min':'green', '30K_min':'blue'}

    for i in hr_dict.keys():
        try:
            mean_df = df.filter(regex = 'mean')
            mean_hr_df_temp = mean_df.filter(regex = i)
            mean_hr_df = mean_hr_df_temp.dropna(axis = 'index')
            std_df = df.filter(regex = 'std')
            std_hr_df_temp = std_df.filter(regex = i)
            std_hr_df = std_hr_df_temp.dropna(axis = 'index')

            y_upper = mean_hr_df.iloc[:,0] + 2*std_hr_df.iloc[:,0]
            y_lower = mean_hr_df.iloc[:,0] - 2*std_hr_df.iloc[:,0]

            i_str = i.replace('_','/')

            fig.add_trace(go.Scatter(x=mean_hr_df.index, y=mean_hr_df.iloc[:,0], marker=dict(color=hr_dict[i], size=8),name=i_str))
            fig.add_trace(go.Scatter(x=y_lower.index,y=y_lower,fill=None, mode='lines', line_color= hr_dict[i], hoveron='points',name='-2'+ "\u03C3"))
            fig.add_trace(go.Scatter(x=y_upper.index,y=y_upper,
                fill='tonexty',hoveron='points',line_color=hr_dict[i],mode='lines',opacity=0.25,name='+2'+ "\u03C3"))
        except:
            continue
    return()

def format_and_save_plot(inc, file_loc):
    axis_dict = {'Mass': 'Normalized Mass', 'MLR': 'Normalized MLR (1/s)', 'Flow': 'Heat Flow Rate (W/g)', 'Cp': 'Apparent Heat Capacity (J/g-K)', 'd': 'DSC Derivative (W/g-K)'}
    keyword = file_loc.split('.html')[0].split('_')[-1]

    fig.update_layout(xaxis_title='Temperature (&deg;C)', font=dict(size=18))
    fig.update_layout(yaxis_title=axis_dict[keyword], title ='Simultaneous Thermal Analysis')

    #Get github hash to display on graph
    repo = git.Repo(search_parent_directories=True)
    sha = repo.head.commit.hexsha
    short_sha = repo.git.rev_parse(sha, short=True)

    fig.add_annotation(dict(font=dict(color='black',size=15),
                                        x=1,
                                        y=1.02,
                                        showarrow=False,
                                        text="Repository Version: " + short_sha,
                                        textangle=0,
                                        xanchor='right',
                                        xref="paper",
                                        yref="paper"))

    fig.write_html(file_loc,include_plotlyjs="cdn")
    plt.close()
    print()

data_dir = '../01_Data/HDPE/'
save_dir = '../03_Charts/HDPE/'

plot_dict = {'Normalized Mass':'Mass', 'Normalized MLR':'MLR', 'Heat Flow Rate':'Heat_Flow', 'Apparent Heat Capacity':'Cp', 'DSC_deriv':'d'}


material = 'HDPE'

plot_data_df = pd.DataFrame()
print(f'{material} STA')
for d_ in os.scandir('../01_Data/HDPE/STA/N2/'):
    data_df = pd.DataFrame()
    reduced_df = pd.DataFrame()
    for f in glob.iglob(f'{d_.path}/*.csv'):
        HR = d_.path.split('/')[-1]
        if 'Meta' in f or '.DS_Store' in f:
            continue
        else:
            # import data for each test

            print(f)

            fid = f.split('/')[-1]
            fid_meta = fid.replace('Data', 'Meta')
            f_meta = f.replace(fid, fid_meta)

            data_temp_df = pd.read_csv(f, header = 0)
            meta_temp_df = pd.read_csv(f_meta).squeeze()
            meta_col_df = meta_temp_df.filter(regex='EXPORT').squeeze()
            mass_ind = meta_col_df.str.find('SAMPLE MASS', start = 0).idxmax()
            m0 = float(meta_temp_df.iloc[mass_ind, 1])

            data_temp_df['Temp (C)']  = data_temp_df.filter(regex='Temp', axis='columns')

            data_temp_df['time (s)'] = data_temp_df.filter(regex='Time', axis='columns')
            data_temp_df['time (s)'] = (data_temp_df['time (s)']-data_temp_df.loc[0,'time (s)'])*60

            data_temp_df['Heating rate (K/s)'] = np.gradient(data_temp_df['Temp (C)'], data_temp_df['time (s)'])

            data_temp_df['Mass/mg'] = m0 + data_temp_df.filter(regex='Mass', axis='columns')
            data_temp_df['nMass'] = data_temp_df['Mass/mg']/data_temp_df.at[0,'Mass/mg']

            data_temp_df['Normalized MLR (1/s)'] = -np.gradient(data_temp_df['nMass'], data_temp_df['time (s)'])
            data_temp_df['Normalized MLR (1/s)'] = apply_savgol_filter(data_temp_df['Normalized MLR (1/s)'])

            test_list = [i for i in data_temp_df.columns.to_list() if 'mW/mg' in i] # determine if DSC is given in mW or mW/mg

            if not test_list:
                data_temp_df['DSC/(mW/mg)'] = data_temp_df.filter(regex='DSC', axis='columns')/m0
            else:
                data_temp_df['DSC/(mW/mg)'] = data_temp_df.filter(regex='DSC', axis='columns')

            data_temp_df['Apparent Heat Capacity (J/g-K)'] = data_temp_df['DSC/(mW/mg)']/data_temp_df['Heating rate (K/s)']

            # data_temp_df['DSC_deriv'] = np.gradient(data_temp_df['nMass'], data_temp_df['Temp (C)'])


            # data_temp_df = pd.read_csv(f, header = 0)
            # data_temp_df.rename(columns = {'##Temp./°C':'Temp (C)', 'Time/min':'time (s)'}, inplace = True)
            # data_temp_df['Mass/%'] = data_temp_df['Mass/%']/data_temp_df.loc[0,'Mass/%']
            # data_temp_df['time (s)'] = (data_temp_df['time (s)']-data_temp_df.loc[0,'time (s)'])*60
            # data_temp_df['Normalized MLR (1/s)'] = -data_temp_df['Mass/%'].diff()/data_temp_df['time (s)'].diff()
            # data_temp_df['Normalized MLR (1/s)'] = apply_savgol_filter(data_temp_df['Normalized MLR (1/s)'])

            col_name = f.split('.csv')[0].split('_')[-1]

            min_lim = data_temp_df['Temp (C)'].iloc[1] - ((data_temp_df['Temp (C)'].iloc[1])%1)
            max_lim = data_temp_df['Temp (C)'].iloc[-1] - ((data_temp_df['Temp (C)'].iloc[-1])%1)

            reduced_df = data_temp_df.loc[:,['Temp (C)', 'nMass', 'Normalized MLR (1/s)', 'DSC/(mW/mg)', 'Apparent Heat Capacity (J/g-K)']]

            # Re-index data

            new_index = np.arange(int(min_lim),int(max_lim)+1)
            new_data = np.empty((len(new_index),))
            new_data[:] = np.nan
            df_dict = {'Temp (C)': new_index, 'Normalized Mass': new_data, 'Normalized MLR (1/s)': new_data, 'Heat Flow Rate (W/g)': new_data, 'Apparent Heat Capacity (J/g-K)': new_data, 'DSC_deriv': new_data}
            temp_df = pd.DataFrame(df_dict)

            # Resample data to every 1 degree
            reduced_df = pd.concat([reduced_df, temp_df], ignore_index = True)
            reduced_df.set_index('Temp (C)', inplace = True)
            reduced_df.sort_index(inplace=True)
            reduced_df.interpolate(method='slinear', axis=0, inplace=True)
            reduced_df = reduced_df.loc[new_index, :]

            reduced_df['Normalized Mass'] = reduced_df.pop('nMass')
            reduced_df['Heat Flow Rate (W/g)'] = reduced_df.pop('DSC/(mW/mg)')
            reduced_df = reduced_df[~reduced_df.index.duplicated(keep='first')]

            # Identify Melting Temperature

            reduced_df['DSC_deriv'] = apply_savgol_filter(reduced_df['Heat Flow Rate (W/g)'], deriv=1)

            dsc = reduced_df['Heat Flow Rate (W/g)'].loc[80:400].to_numpy()
            dsc_deriv = reduced_df['DSC_deriv'].loc[80:400].to_numpy()
            combined = np.vstack((dsc, dsc_deriv)).T

            cost_df = pd.DataFrame()

            cost_L1 = rpt.Window(width = 10, model = 'l1', jump = 1).fit(dsc)
            cost_L2 = rpt.Window(width = 10, model = 'l2', jump = 1).fit(dsc)
            cost_RBF = rpt.Window(width = 10, model = 'rbf', jump = 1).fit(dsc)
            cost_Normal = rpt.Window(width = 10, model = 'normal', jump = 1).fit(dsc)
            cost_Linear = rpt.Window(width = 10, model = 'linear', jump = 1).fit(dsc)
            cost_AR = rpt.Window(width = 10, model = 'ar', jump = 1).fit(dsc)

            cost_df['L1'] = cost_L1.score
            cost_df['L2'] = cost_L2.score
            cost_df['Normal'] = cost_Normal.score
            cost_df['RBF'] = cost_RBF.score
            cost_df['Linear'] = cost_Linear.score
            cost_df['AR'] = cost_AR.score

            L1_bkps = cost_L1.predict(n_bkps = 2)
            L2_bkps = cost_L2.predict(n_bkps = 2)
            RBF_bkps = cost_RBF.predict(n_bkps = 2)
            Normal_bkps = cost_Normal.predict(n_bkps = 2)
            Linear_bkps = cost_Linear.predict(n_bkps = 2)
            AR_bkps = cost_AR.predict(n_bkps = 2)

            print(f'L1_bkps: {L1_bkps}')
            print(f'L2_bkps: {L1_bkps}')
            print(f'Normal_bkps: {L1_bkps}')
            print(f'RBF_bkps: {L1_bkps}')
            print(f'Linear_bkps: {L1_bkps}')
            print(f'AR_bkps: {L1_bkps}')


            cost_df.to_csv(f'../01_Data/HDPE/STA/N2/cost.csv')

            algo = rpt.Pelt(model='ar').fit(combined)
            result = algo.predict(pen = 6)

            print(result)

            max_mlr = reduced_df['Normalized MLR (1/s)'].max()
            mlr_threshold = 0.1*max_mlr
            max_d_dsc = reduced_df['DSC_deriv'].max()
            d_dsc_threshold = 0.1*max_d_dsc

            signs = np.sign(reduced_df['DSC_deriv']).diff().ne(0)
            signs_list = signs.index[signs].tolist()

            for i in signs_list:
                if i < 60:
                    continue
                elif reduced_df.abs().loc[i-5,'DSC_deriv'] > d_dsc_threshold and reduced_df.abs().loc[i+5,'DSC_deriv'] > d_dsc_threshold:
                    if reduced_df.abs().loc[i,'Normalized MLR (1/s)'] < mlr_threshold:
                        print(i)

            if data_df.empty:
                data_df = reduced_df
            else:
                data_df = pd.concat([data_df, reduced_df], axis = 1)

    for m in plot_dict.keys():
        data_sub = data_df.filter(regex = m)
        plot_data_df.loc[:,f'{m} {HR} mean'] = data_df.filter(regex = m).mean(axis = 1)
        plot_data_df.loc[:,f'{m} {HR} std'] = data_df.filter(regex = m).std(axis = 1)

# plot_data_df.to_csv(f'{data_dir}{material}/STA/N2/TEST_html.csv')

plot_dir = f'../03_Charts/{material}/STA/N2/'

plot_inc = {'Mass': 0.2, 'MLR': 0.001, 'Heat_Flow': 0.5, 'Cp': 0.5, 'd': 0.1}

for m in plot_dict.keys():    
    fig = go.Figure()

    plot_data = plot_data_df.filter(regex = m)
    plot_mean_data(plot_data)

    inc = plot_inc[plot_dict[m]]

    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)

    suffix = plot_dict[m]
    format_and_save_plot(inc, f'{plot_dir}{material}_STA_{suffix}.html')