import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import os


def file_selector(folder_path='.'):
    filenames = os.listdir(folder_path)
    selected_filename = st.selectbox('Select a file', sorted(filenames))

    return os.path.join(folder_path, selected_filename)


def to_lower_case():
    return lambda text: str(text).lower()


@st.cache_data
def load_data(filename):
    data = pd.read_csv(filename)
    lowercase = to_lower_case()
    data.rename(lowercase, axis=1, inplace=True)

    return data


# initialize global variables
final_table = pd.DataFrame()
COUNTS = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]

# design title of page
st.title('Behavioral Profiling Algorithm', )
st.markdown('_powered by_  **GRL Lab**  :rat:')

st.subheader('1. Upload your data file')
data_file = st.file_uploader("Upload a CSV file to start analysis",
                             help="If you don't have your file prepared according to the predefined format or you "
                                  "don't know how to format it, please download a data file template through the "
                                  "Download button below.")

# button for downloading a clean data file template
if os.path.isfile("resources/datafile_template.csv"):
    with open("resources/datafile_template.csv", "rb") as file:
        btn = st.download_button(
                label="Download data file template",
                data=file,
                file_name="datafile_template.csv",
                mime="text/csv")

# after selecting a data file
template_file = False
if data_file:
    # 4. option to load template file
    st.subheader('Use a parameter directions file you saved before?')
    use_template_file = st.radio(' ', ('Yes', 'No'), 1, horizontal=True,
                                 help='Use a template file to preferences for selected parameters for analysis')
    if use_template_file == 'Yes':
        # st.set_option('deprecation.showfileUploaderEncoding', False)
        template_file = \
            st.file_uploader('Select directions preferences template CSV file', type='csv',
                             help="The preferences template file will set the  up / down directions of the"
                                  " selected parameters. If you don't have a template file you will be able to get it"
                                  " after you first selected the Up / Down preferences for you parameters")

    # read data file
    data_df = load_data(data_file)
    # convert non numeric values to nan
    data_df[data_df.columns[2:]] = data_df[data_df.columns[2:]].apply(
        lambda value: pd.to_numeric(value, errors='coerce'))
    group_col = data_df.columns[0]

    subject_col = data_df.columns[1]

    # read template file
    template_df = pd.DataFrame()
    if template_file and use_template_file == 'Yes':
        template_df = load_data(template_file)

    group_list = {'group_' + str(i): {'selected': True} for i in data_df[group_col]}
    if use_template_file == 'Yes' and not template_file:
        st.write('You need to select a template file to continue')
    else:
        if use_template_file == 'Yes':
            param_list = {i: {'selected': False, 'direction': template_df.loc[0, i]} for i in template_df.columns}

        else:
            param_list = {i: {'selected': False, 'direction': 'both', 'dir_icon': ':arrow_up_down:'} for i in
                          data_df.columns[2:]}
        # control group selection. defaults to first group in data file
        control_group = st.selectbox('Select control group', list(group_list.keys()),
                                     help='Control group can be manually changed. The default is the first group in'
                                          ' the data file')
        st.subheader('2. Select groups for analysis')
        for group in group_list:
            if group != control_group:
                group_list[group]['selected'] = st.checkbox(group, group, group + '_key')
        # 3. define the parameters list
        st.subheader('3. Select parameters for analysis and set their direction')
        directions = ['both', 'above control', 'below control']
        # col1, col2 = st.columns(2)

        for param in param_list:
            col1, col2 = st.columns(2)
            # 3. allow manual changes for parameter inclusion
            param_list[param]['selected'] = col1.checkbox(param, value=param_list[param]['selected'], key=param)
            # 4. allow manual changes for direction
            param_list[param]['direction'] = col2.selectbox(param + ' direction', directions,
                                                            index=directions.index(param_list[param]['direction']))

            # update the arrow icons directions
            if param_list[param]['direction'] == 'both':
                param_list[param]['dir_icon'] = ':arrow_up_down:'
            elif param_list[param]['direction'] == 'above control':
                param_list[param]['dir_icon'] = ':arrow_up_small:'
            else:
                param_list[param]['dir_icon'] = ':arrow_down_small:'

        # 4. save template to file
        save_template_file = data_file.name[:-4] + '_direction_preferences.csv'
        st.download_button('Save directions preferences file for later use?',
                           data=pd.DataFrame.from_dict(param_list).drop('selected').to_csv(index=False),
                           file_name=save_template_file,
                           mime="text/csv",
                           help='You can use this file when you come back around next time')

        # 1. collect group means and sd into dataframes
        group_mean = pd.DataFrame()
        group_std = pd.DataFrame()
        # loop groups and calculate mean and sd + remove unwanted columns
        for group in list(i for i in group_list.keys() if group_list[i]['selected']):
            # collect all the groups means
            group_mean[group] = data_df[data_df[group_col] == int(group[-1])][param_list.keys()].mean()
            # collect all the groups SDs
            group_std[group] = data_df[data_df[group_col] == int(group[-1])][param_list.keys()].std()

        # 2.1. set the difference between control and other groups mean to be included
        mean_difference = st.slider('Select mean differences between control and experiment groups', 0, 100, 30, 5)
        mean_difference = mean_difference / 100

        # 2.2. set the difference between control and other groups deviance to be included
        deviation_difference = \
            st.slider('Select deviation differences between control and experiment groups', 0, 100, 30, 5)
        deviation_difference = deviation_difference / 100

        # 2.3. find parameters that should be included
        for group in list(i for i in group_list.keys() if group_list[i]['selected']):
            for param in param_list:  # calculate deviation difference for all the parameters columns
                if group_std[group][param] == 0:
                    calculated_deviation_difference = 0
                else:
                    calculated_deviation_difference = group_std[group][param] / group_std[control_group][param]
                if (((1 - deviation_difference) > calculated_deviation_difference > (1 + deviation_difference)) or
                        ((abs(group_mean[group][param] - group_mean[control_group][param]) /
                          group_mean[control_group][param]) > mean_difference)):
                    param_list[param]['selected'] = True

        # 3. define the parameters list
        st.subheader('3. Select parameters for analysis')

        # allow updating the selected parameters
        for param in param_list:
            col1, col2 = st.columns(2)
            # 3. allow manual changes for parameter inclusion
            param_list[param]['selected'] = col1.checkbox(param, value=param_list[param]['selected'])

            # show direction arrows
            col2.markdown(param_list[param]['dir_icon'])

        included_group_list = list(i for i in group_list.keys() if group_list[i]['selected'])
        included_param_list = list(i for i in param_list.keys() if param_list[i]['selected'])

        # group_list_for_dev = {}
        # for group in included_group_list:
        #     if group != control_group:
        #         group_list_for_dev[group] = {}
        #         group_list_for_dev[group]['selected'] = st.checkbox(group, group)

        # keep the optimized and weighted maximum difference between control and group
        max_of_max = {'SD': 0.5, '# of params': 0, 'max diff': 0,
                      'weighted': 0}

        # 5. find the sd that has the largest difference between control and experiment groups
        true_columns_dict = {}
        true_false_dict = {}
        for_pie = {}
        group_len = {}
        for sd in range(5, 21):
            sd = sd / 10
            # create the final count files infrastructure in the size of included groups x number of parameters
            true_columns_dict[sd] = pd.DataFrame()
            true_columns_dict[sd]['count'] = COUNTS[:len(param_list)]
            for group in list(i for i in group_list.keys() if group_list[i]['selected']):
                true_columns_dict[sd][group] = 0
            true_columns_dict[sd] = true_columns_dict[sd].set_index('count')
            true_false_dict[sd] = pd.DataFrame()
            true_false_dict[sd][[group_col, subject_col]] = data_df[[group_col, subject_col]]
            group_len[sd] = {}
            # check the inclusion or exclusion for each animal in each parameter against the control group mean and SD
            for group in included_group_list:  # loop thorough the included groups
                for param in included_param_list:  # calculate for each of the parameters
                    standard_param_col = (data_df[param] - group_mean[control_group][param]) /\
                                         group_std[control_group][param]
                    if param_list[param]['direction'] == 'both':
                        true_false_dict[sd][param] = abs(standard_param_col) >= sd
                    elif param_list[param]['direction'] == 'above control':
                        true_false_dict[sd][param] = standard_param_col >= sd
                    else:
                        true_false_dict[sd][param] = standard_param_col <= -sd
                group_len[sd][group] = data_df[data_df[group_col] == int(group[-1])].shape[0]

            true_false_dict[sd]['sum'] = true_false_dict[sd][included_param_list].sum(axis=1)

            # calculate the percentage of affected animals per group per level
            # (if 2 is selected there are high_start and low levels)
            for group in included_group_list:  # loop thorough the included groups
                percentages = []
                for count in true_columns_dict[sd].index:
                    percentages.append(true_false_dict[sd][(true_false_dict[sd]['sum'] >= count) &
                                                           (true_false_dict[sd][group_col] == int(group[-1]))].count()
                                       ['sum'] / group_len[sd][group] * 100)
                true_columns_dict[sd][group] = percentages

            # test for max difference only if control group value is under 20%
            true_sums_counts_cut = true_columns_dict[sd][true_columns_dict[sd][control_group] <= 20]

            # calculate the maximum difference between any of the groups and the control group
            true_sums_counts_cut.loc[:, 'max_diff'] = \
                true_sums_counts_cut.loc[:, included_group_list].max(1) - true_sums_counts_cut[control_group]

            # calculate the weighted index as max_diff divided by the number of parameters

            true_sums_counts_cut.loc[:, 'weighted'] = true_sums_counts_cut['max_diff'] * true_sums_counts_cut.index

            # replace value if weighted is grater than the value collected until now
            if true_sums_counts_cut['weighted'].max() > max_of_max['weighted']:
                max_index = true_sums_counts_cut['weighted'].idxmax()
                max_of_max = {'SD': sd,
                              '# of params': int(max_index),
                              'max diff': true_sums_counts_cut.loc[max_index, 'max_diff'],
                              'weighted': true_sums_counts_cut.loc[max_index, 'weighted']}
            true_columns_dict[sd].index = true_columns_dict[sd].index.astype(int)
        # true_sums_counts_cut
        # display the selected optimal result in table format
        st.subheader('The optimal weighted maximum difference between control and exp groups')
        # CSS to inject contained in a string
        hide_table_row_index = """
                    <style>
                    thead tr th:first-child {display:none}
                    tbody th {display:none}
                    </style>
                    """
        # inject CSS with Markdown
        st.markdown(hide_table_row_index, unsafe_allow_html=True)
        st.table(pd.DataFrame(max_of_max, index=[0]))

        # 6. show the sd slider with calculated sd value as default. allow selecting 2 limits (high, low)
        st.subheader('4. Select SD range to set limit between affected and unaffected animals')
        dev_high = st.slider('Select SD range high',
                             0.5, 2.0, max_of_max['SD'], 0.1,
                             help='If medium level is selected this will set the limit between highly affected and '
                                  'medium affected animal')
        second_level = st.checkbox('Add a medium level?',
                                   help='The default is to have affected / not affected animals. '
                                        'If a medium level is added, the affected animals will be divided into 2 '
                                        'levels - highly affected and medium affected.')
        final_table[group_col] = data_df[group_col]  # final table
        final_table[subject_col] = data_df[subject_col]  # final table
        true_columns_dict[dev_high]['Number of parameters'] = true_columns_dict[dev_high].index
        if not second_level:  # only high level is selected
            # rearrange dataframe for line chart, format and draw line chart
            df_melt = pd.melt(true_columns_dict[dev_high],
                              value_vars=included_group_list,
                              id_vars='Number of parameters',
                              var_name='Group',
                              value_name='Percentage')
            c = px.line(df_melt, x="Number of parameters", y='Percentage',
                        color="Group",
                        height=400, range_x=[2, len(included_param_list) + 1], range_y=[0, 100])
            c.add_vline(x=max_of_max['# of params'], line_dash="dash", line_color="darkgray")
            c.layout.plot_bgcolor = 'white'
            c.layout.title = 'Percentage of affected subject for each parameter count'
            c.update_xaxes(dtick=1)
            st.plotly_chart(c)

            # allow user to get pie charts for different parameter counts
            num_of_params = st.slider('Number of parameters to display in pie charts',
                                      2,
                                      len(included_param_list),
                                      max_of_max['# of params'],
                                      1)

            # 11 + 12. create pie charts for 1 level
            for group in included_group_list:
                fig1, ax1 = plt.subplots()
                labels = 'Affected', 'Unaffected'
                explode = (0.1, 0)  # only "explode" the first slice_high
                color = ['0.7', '0.85']
                slice_high = int(true_columns_dict[dev_high].loc[num_of_params, group])
                sizes = [slice_high / 100, 1 - (slice_high / 100)]
                # 'Sizes =', sizes
                pie_df = pd.DataFrame(sizes)

                ax1.set_title('Group ' + group[-1] + ' / ' + 'SD: ' + str(dev_high) + ' / Params: ' +
                              str(num_of_params),
                              fontsize=18)
                ax1.pie(sizes,
                        explode=explode,
                        labels=labels,
                        autopct='%1.1f%%',
                        shadow=True,
                        startangle=90,
                        colors=color,
                        textprops={'fontsize': 14})
                ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
                st.pyplot(fig1)

                # 13. create the final table of subjects and their respective list of affected parameters
                # final_table.loc[true_false_dict[dev_high]['sum'].index, 'Affected'] = \
                #     true_false_dict[dev_high]['sum'] >= max_of_max['# of params']
                final_table['Affected'] = true_false_dict[dev_high]['sum'] >= max_of_max['# of params']
                only_true_false_df = true_false_dict[dev_high].drop([group_col, subject_col, 'sum'], axis=1)
                attended_params = only_true_false_df.apply(lambda row: row.index[row.astype(bool)].tolist(), 1)  #
                final_table.loc[true_false_dict[dev_high]['sum'].index, 'Params'] = attended_params

        else:  # selected to use medium level
            dev_low = round(st.slider('Select SD range for medium affected', 0.5, dev_high, dev_high * 0.7, 0.05), 2)
            for group in included_group_list:  # loop thorough the included groups
                for param in included_param_list:  # calculate for each of the parameters
                    standard_param_col = \
                        (data_df[param] - group_mean[control_group][param]) / group_std[control_group][param]
                if param_list[param]['direction'] == 'both':
                    true_false_dict[dev_high][param + '_med'] = (abs(standard_param_col) < dev_high) & \
                                                                (abs(standard_param_col) >= dev_low)
                elif param_list[param]['direction'] == 'above control':
                    true_false_dict[dev_high][param + '_med'] = (standard_param_col < dev_high) & \
                                                                (standard_param_col >= dev_low)
                else:
                    true_false_dict[dev_high][param + '_med'] = (standard_param_col > -dev_high) & \
                                                                (standard_param_col <= -dev_low)

            # 7. count and find percent of own group of affected animals for 2 levels - high and medium affected
            true_false_dict[dev_high]['sum'] = true_false_dict[dev_high][included_param_list].sum(axis=1)
            true_false_dict[dev_high]['perc_of_included_high'] = \
                true_false_dict[dev_high]['sum'] / len(included_param_list) * 100
            true_false_dict[dev_high]['sum_med'] = \
                true_false_dict[dev_high].loc[:, [x for x in true_false_dict[dev_high].columns
                                                  if x.endswith('_med')]].sum(axis=1)
            true_false_dict[dev_high]['perc_of_included_med'] = \
                true_false_dict[dev_high]['sum_med'] / len(included_param_list) * 100

            # 8. calculate the correct value of affected for each subject
            true_false_dict[dev_high]['affect_value_corrected'] = \
                true_false_dict[dev_high]['perc_of_included_high'] + \
                (true_false_dict[dev_high]['perc_of_included_med'] / 2)
            # 9. calculate low-med point by the mean and sd of 'affect_value_corrected' for control group
            control_values = \
                true_false_dict[dev_high]['affect_value_corrected'][true_false_dict[dev_high]['group'] ==
                                                                    int(control_group[-1])]
            medium_default = int(control_values.mean() + control_values.std())

            # 10. calculate med-high point by the mean of remaining value' - (max + min) / 2
            medium_start = st.slider('Select medium cut point', 0, 100, medium_default, 1)
            high_series = true_false_dict[dev_high]['affect_value_corrected'][
                true_false_dict[dev_high]['affect_value_corrected'] > medium_default]
            high_default = int((high_series.max() + high_series.min()) / 2)
            high_start = st.slider('Select high cut point', medium_start, 100, high_default + 1, 1)

            # 12. create pie charts for 2 levels
            for group in included_group_list:
                for_pie[group] = {}
                highly_affected_count = round(
                    true_false_dict[dev_high][(true_false_dict[dev_high]['affect_value_corrected'] >
                                               high_start) & (true_false_dict[dev_high]['group'] ==
                                                              int(group[-1]))]['group'].count() /
                    group_len[dev_high][group] * 100, 1)
                # true_false_dict[dev_high]['group'] == int(group[-1])
                medium_affected_count = round(
                    true_false_dict[dev_high][(true_false_dict[dev_high]['affect_value_corrected'] < high_start) &
                                              (true_false_dict[dev_high]['affect_value_corrected'] > medium_start) &
                                              (true_false_dict[dev_high]['group'] == int(group[-1]))]['group'].count() /
                    group_len[dev_high][group] * 100, 1)

                labels = ['Highly Affected', 'Medium Affected', 'Not Affected']
                explode = (0.1, 0.1, 0)  # only "explode" the first slice_high
                color = ['0.7', '0.6', '0.85']
                sizes = [highly_affected_count,
                         medium_affected_count,
                         100 - (highly_affected_count + medium_affected_count)]
                fig1, ax1 = plt.subplots()
                ax1.set_title('Group ' + group[-1] + ' / ' + 'SD (high / medium): ' + str(dev_high) +
                              ' / ' + str(dev_low), fontsize=18)

                ax1.pie(sizes,
                        explode=explode,
                        labels=labels,
                        autopct='%1.1f%%',
                        shadow=True,
                        startangle=90,
                        colors=color,
                        textprops={'fontsize': 14})
                ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
                st.pyplot(fig1)

                # 13. create the final table of subjects and their respective list of affected parameters
                final_table.loc[true_false_dict[dev_high]['sum'].index, 'Affected_high'] = \
                    true_false_dict[dev_high]['sum'] >= max_of_max['# of params']
                final_table.loc[true_false_dict[dev_high]['sum_med'].index, 'Affected_med'] = \
                    (max_of_max['# of params'] >= true_false_dict[dev_high]['sum_med']) & \
                    (true_false_dict[dev_high]['sum_med'] >= int(max_of_max['# of params'] * (dev_low / dev_high)))

                high_columns = included_param_list
                med_columns = \
                    [c + '_med' for c in included_param_list if c + '_med' in true_false_dict[dev_high].columns]
                # only_true_false_low_df = only_true_false_df[[columns_low]]
                attended_params_high = true_false_dict[dev_high][high_columns].apply(
                    lambda row: row.index[row.astype(bool)].tolist(), 1)  #
                attended_params_med = true_false_dict[dev_high][med_columns].apply(
                    lambda row: row.index[row.astype(bool)].tolist(), 1)  #
                final_table.loc[true_false_dict[dev_high]['sum'].index, 'Params_high'] = attended_params_high
                final_table.loc[true_false_dict[dev_high]['sum_med'].index, 'Params_med'] = attended_params_med

        # 13. create the final table of subjects and their respective list of affected parameters
        st.subheader('Final table')
        st.dataframe(final_table)

        # button for downloading the final table
        if second_level:
            levels = 2
        else:
            levels = 1
        final_table_filename = 'final_table_' + str(levels) + '_levels' + data_file.name  # data_file[2:]
        st.download_button(label="Save table as CSV",
                           data=final_table.to_csv(index=False),
                           file_name=final_table_filename,
                           mime="text/csv")
