import streamlit as st
import pandas as pd
from itertools import combinations


@st.cache
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode('utf-8')


# def file_selector(folder_path='.'):
#     filenames = os.listdir(folder_path)
#     selected_filename = st.selectbox('Select a file', sorted(filenames))
#
#     return os.path.join(folder_path, selected_filename)


def to_lower_case():
    return lambda text: str(text).lower()


@st.cache(allow_output_mutation=True)
def load_data(filename):
    data = pd.read_csv(filename)
    lowercase = to_lower_case()
    data.rename(lowercase, axis=1, inplace=True)

    return data


final_table = pd.DataFrame()
COUNTS = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]

st.write("# Analyse Paired Differences")
st.markdown(
    """
    Read csv data files
    """)

data_file = st.file_uploader('Choose a data file', type='csv')

if data_file:
    # # 4. option to load template file
    # use_template_file = st.radio('Upload a template file?', ('Yes', 'No'), 1)
    # if use_template_file == 'Yes':
    #     st.set_option('deprecation.showfileUploaderEncoding', False)
    #     template_file = st.file_uploader('Select directions template a .csv file', type='csv')

    # read data file
    data_df = load_data(data_file)
    # convert non numeric values to nan
    data_df[data_df.columns[2:]] = data_df[data_df.columns[2:]].apply(lambda value: pd.to_numeric(value, errors='coerce'))
    group_col = data_df.columns[0]
    subject_col = data_df.columns[1]
    subject_list = data_df[subject_col]

    # get tasks and their parameter list from file
    task_groups = {}
    for col in data_df.columns[2:]:
        task_name = col.split('_')[0]
        if task_name not in task_groups:
            task_groups[task_name] = []
        task_groups[task_name].append(col)

    # for paired - calculate differences per subject per parameter
    per_subject_diffs = data_df.copy()
    per_subject_diffs = per_subject_diffs.groupby([subject_col])[per_subject_diffs.columns].diff()
    per_subject_diffs[subject_col] = subject_list
    per_subject_diffs = per_subject_diffs[per_subject_diffs[group_col] == 1].set_index(subject_col)
    per_subject_diffs = per_subject_diffs.drop(columns=group_col)

    group_list = {'group_' + str(i): {'selected': 1} for i in data_df[group_col]}
    param_list = {i: {'selected': False, 'direction': 'both'} for i in data_df.columns[2:]}

    # 1. collect group means and sd into dataframes
    group_mean = pd.DataFrame()
    group_std = pd.DataFrame()
    for group in list(i for i in group_list.keys() if group_list[i]['selected']):  # loop groups and calculate mean and sd + remove unwanted columns
        group_mean[group] = data_df[data_df[group_col] == int(group[-1])][list(param_list)].mean()  # collect all of the groups means
        group_std[group] = data_df[data_df[group_col] == int(group[-1])][list(param_list)].std()  # collect all of the groups SDs
    group_std

    # 1.1 (Roee) - set mode to paired
    grouped_diffs = pd.DataFrame()
    group_mean = group_mean.rename(columns={group_mean.columns[0]: 'Pre', group_mean.columns[1]: 'Post'})
    delta_std = 1.0
    # group_mean['diff'] = group_mean['group_1'] - group_mean['group_0']
    # group_mean['diff_std=' + str(delta_std)] = group_mean['diff'].std() * delta_std
    # grouped_diffs['diff'] = group_mean['Post'] - group_mean['Pre']
    grouped_diffs['mean'] = per_subject_diffs.mean()
    grouped_diffs['count'] = per_subject_diffs.count()
    std_column_name = 'std_' + str(delta_std)
    grouped_diffs[std_column_name] = per_subject_diffs.std() * delta_std
    'Per parameter group diff', grouped_diffs
    'Per subject per parameter diff', per_subject_diffs

    # delta_std = st.slider('Select % of differences between subjects delta and mean group delta', 1.0, 2.0, 1.0, 0.1)
    stds = list(float(x / 10) for x in range(10, 21))
    std_df = pd.DataFrame(index=range(1, len(grouped_diffs) + 1))
    show_list = [1.0, 1.5, 2.0]
    affected = {}
    affected_full = {}
    affected_full_percentages = {}
    for std in stds:
        grouped_diffs[std_column_name] = per_subject_diffs.std() * std
        grouped_diffs = grouped_diffs.rename(columns={std_column_name: 'std_' + str(std)})
        affected[std] = per_subject_diffs.copy()
        affected_full[std] = per_subject_diffs.copy()

        grouped_diffs['+1'] = 0
        grouped_diffs['-1'] = 0
        grouped_diffs['0'] = 0
        for i, row in grouped_diffs.iterrows():
            for j, subject in per_subject_diffs[i].dropna().items():
                if (row['mean'] - row['std_' + str(std)] > subject) or \
                        (subject > row['mean'] + row['std_' + str(std)]):
                    # affected[std]
                    affected[std].loc[j, i] = 1
                else:
                    affected[std].loc[j, i] = 0
                if subject > row['mean'] + row['std_' + str(std)]:
                    affected_full[std].loc[j, i] = 1
                    grouped_diffs.loc[i, '+1'] += 1
                elif subject < row['mean'] - row['std_' + str(std)]:
                    affected_full[std].loc[j, i] = -1
                    grouped_diffs.loc[i, '-1'] += 1
                else:
                    affected_full[std].loc[j, i] = 0
                    grouped_diffs.loc[i, '0'] += 1

        affected[std]['affected'] = affected[std].sum(axis=1)
        affected_full[std]['affected'] = affected[std]['affected']
        for task, groups in task_groups.items():
            affected[std]['affected_' + task] = affected[std].loc[:, task_groups[task]].sum(axis=1)
            affected_full[std]['affected_' + task] = affected[std]['affected_' + task]
            affected_full[std]['bin_affected_' + task] = affected_full[std]['affected_' + task].astype(bool).astype(int)
        grouped_diffs['affected'] = grouped_diffs['+1'] + grouped_diffs['-1']
        for parameters in range(1, len(grouped_diffs) + 1):
            std_df.loc[parameters, '{:.1f}'.format(std)] = \
                len(affected[std].loc[affected[std]['affected'] >= parameters]) / len(per_subject_diffs) * 100
        if std in show_list:
            # std, grouped_diffs
            std, affected[std]
        # show table of standard deviations with included affected subjects by number of parameters percentages
        # affected_full[std]

        # find all task combinations
        task_combs_names = {}
        # 'task_groups', task_groups
        for i in range(1, len(task_groups.keys()) + 1):
            task_combs_names[i] = []
            task_combs = list(combinations(task_groups.keys(), i))
            for task in task_combs:
                task_comb_name = 'affected_' + '_'.join(task)
                if i > 1:
                    affected_full[std][task_comb_name] = 0
                    affected_full[std]['bin_' + task_comb_name] = 1
                    for j in range(i):
                        affected_full[std][task_comb_name] += affected_full[std]['affected_' + task[j]]
                        affected_full[std]['bin_' + task_comb_name] = \
                            affected_full[std]['bin_' + task_comb_name] & affected_full[std]['bin_affected_' + task[j]]

        affected_full_percentages[std] = {}
        for col in [col for col in affected_full[std] if col.startswith('bin_')]:
            affected_full_percentages[std][col] = affected_full[std][col].sum() / len(affected_full[std][col]) * 100
    st.write('Table of percentage of affected subjects by number of paramters')
    std_df


    # display final table with an option to choose standard deviation
    str_stds = list(str(std) for std in stds)
    std = float(st.selectbox('select SD to view', str_stds, str_stds.index('1.0')))
    affected_full_percentages[std]
    affected_full[std]

    # download final table
    filename = 'affected_sd_' + str(std) + '.csv'
    download_data = convert_df(affected_full[std])
    st.download_button(label='Download CSV',
                       data=download_data,
                       file_name=filename,
                       mime='text/csv')
