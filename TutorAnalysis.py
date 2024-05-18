import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import re
import seaborn as sns
import numpy as np

st.header("Tutor Analysis")
st.write("By Juan Carlos Ferreyra")

data_file = None
df = None
df_counts = None
def get_data_csv(data):
    df = pd.read_csv(data)
    return preprocess_data(df)


def get_data_excel(data):
    df = pd.read_excel(data)
    return preprocess_data(df)


def get_data_gs(url):
    st.write("Original URL:", url)
    try:
        pattern = r'https://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9-_]+)(/edit#gid=(\d+)|/edit.*)?'
        replacement = lambda m: f'https://docs.google.com/spreadsheets/d/{m.group(1)}/export?format=csv' + (
            f'&gid={m.group(3)}' if m.group(3) else '')
        new_url = re.sub(pattern, replacement, url)
        st.write("CSV Export URL:", new_url)
        df = pd.read_csv(new_url)
        st.write("Data loaded from Google Sheets:", df.head())
        return preprocess_data(df)
    except Exception as e:
        st.error(f"Failed to load data from Google Sheets: {e}")
        return None


def preprocess_data(df):
    st.write("Initial data sample:", df.head())

    df['Course'] = df['Course'].fillna('Unknown')

    df['Course'] = df['Course'].apply(
        lambda x: "I'm not here for help with a course." if "I'm not here for help" in x else x)

    df['Tutor / Reason'] = df['Tutor / Reason'].fillna('')
    df = df[~df['Tutor / Reason'].str.contains("Jumpstart Session", na=False)]

    df.dropna(subset=['Timestamp', 'Your Name', 'Where are you?', 'Course', 'Tutor / Reason'], inplace=True)

    df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
    df.dropna(subset=['Timestamp'], inplace=True)

    df['Year'] = df['Timestamp'].dt.year
    df['Month'] = df['Timestamp'].dt.month
    df['Day'] = df['Timestamp'].dt.day
    df['Hour'] = df['Timestamp'].dt.hour
    df['Day_of_Week_N'] = df['Timestamp'].dt.dayofweek

    day_type = {0: 'Weekday', 1: 'Weekday', 2: 'Weekday', 3: 'Weekday', 4: 'Weekday', 5: 'Weekend', 6: 'Weekend'}
    df['Day_Type'] = df['Day_of_Week_N'].replace(day_type)

    date_mapping = {0: 'Monday', 1: 'Tuesday', 2: 'Wednesday', 3: 'Thursday', 4: 'Friday', 5: 'Saturday', 6: 'Sunday'}
    df['Day_of_Week'] = df['Day_of_Week_N'].replace(date_mapping)

    df['Course Prefix'] = df['Course'].apply(
        lambda x: "No Course (Visit)" if x == "I'm not here for help with a course." or x== "Unknown" else x[:6])

    st.write("Final data sample after preprocessing:", df.head())
    return df


def generate_course_mapping(df):
    if 'Course Prefix' not in df.columns:
        st.error("Error: 'Course Prefix' column is missing in the DataFrame.")
        return {}
    unique_courses = df['Course Prefix'].unique()
    mapping = {}
    for course in unique_courses:
        if course == "I'm not here for help with a course.":
            mapping[course] = 'No Course (Visit)'
        else:
            mapped_value = course.replace(' ', '')
            mapping[course] = mapped_value

    return mapping

def check_headers(df):
    required_columns = ['Timestamp', 'Your Name', 'Where are you?', 'Course', 'Tutor / Reason']
    if not all(column in df.columns for column in required_columns):
        missing = set(required_columns) - set(df.columns)
        st.error(f"Missing columns in the dataset: {missing}")
        return False
    return True


tab1, tab2, tab3, tab4, tab5 = st.tabs(["Main Page", "Classes Analysis", "Visualizations of Visitors","Visualizations Indivudal Tutors", "Visualizations Time"])


with tab1:
    st.write(
        "Hello! Welcome to the Tutor Analysis Project. Please ensure your data file contains the following headers:")
    headers = pd.DataFrame(columns=['Timestamp', 'Your Name', 'Where are you?', 'Course', 'Tutor / Reason'])
    st.table(headers)
    data_file_type = st.radio("Which file type is your document?", ["Excel", "Google Sheets", "CSV"])

    if data_file_type == "Google Sheets":
        url = st.text_input("Paste the URL of your Google Sheets here:")
        if url and st.button("Load Google Sheets Data"):
            df = get_data_gs(url)
            if df is not None and check_headers(df):
                st.session_state.df = df
                st.dataframe(df[['Timestamp', 'Your Name', 'Where are you?', 'Course', 'Tutor / Reason']])
                course_mapping = generate_course_mapping(df)
                st.session_state.course_mapping = course_mapping
                st.write("Course Mapping:")
                st.json(course_mapping)
                st.success("Data loaded successfully! You can now proceed to other tabs for further analysis.")
    else:
        data_file = st.file_uploader("Choose a file", type=['xls', 'xlsx', 'csv'])
        if data_file is not None and st.button("Load Data"):
            if data_file_type == "Excel":
                df = get_data_excel(data_file)
            elif data_file_type == "CSV":
                df = get_data_csv(data_file)
            if df is not None and check_headers(df):
                st.session_state.df = df
                st.dataframe(df[['Timestamp', 'Your Name', 'Where are you?', 'Course', 'Tutor / Reason']])
                course_mapping = generate_course_mapping(df)
                st.session_state.course_mapping = course_mapping
                st.write("Course Mapping:")
                st.json(course_mapping)
                st.success("Data loaded successfully! You can now proceed to other tabs for further analysis.")
with tab2:
    st.header("Number of Students per Course ")
    if 'df' in st.session_state and not st.session_state.df.empty:
        df = st.session_state.df
        students_per_class = df['Course'].value_counts()

        df_counts = pd.DataFrame({'Course': students_per_class.index, 'Count': students_per_class.values})
        df_counts = df_counts.sort_values('Count', ascending=False)

        plt.figure(figsize=(10, 6))
        sns_plot = sns.barplot(x='Count', y='Course', data=df_counts, order=df_counts['Course'])
        plt.title('Number of Students per Course')

        for p in sns_plot.patches:
            sns_plot.annotate(format(p.get_width(), '.0f'),
                              (p.get_width(), p.get_y() + p.get_height() / 2),
                              ha='center', va='center',
                              xytext=(20, 0), textcoords='offset points')
        st.pyplot(plt)
    else:
        st.error("Data is not available. Please upload data in the 'Main Page' tab.")

    st.dataframe(df_counts)

    st.header("Percentage of Students per Course")
    if 'df' in st.session_state and not st.session_state.df.empty:
        df = st.session_state.df
        percentage_per_class = (df['Course'].value_counts() / len(df)) * 100
        df_percentage = pd.DataFrame({'Course': percentage_per_class.index, 'Percentage': percentage_per_class.values})

        threshold = 5
        df_percentage.loc[df_percentage['Percentage'] < threshold, 'Course'] = 'Other Courses'
        df_percentage = df_percentage.groupby('Course', as_index=False)['Percentage'].sum()

        plt.figure(figsize=(10, 6))
        plt.pie(df_percentage['Percentage'], labels=df_percentage['Course'], autopct='%1.1f%%',
                colors=sns.color_palette('viridis'), startangle=140)
        plt.title('Percentage of Students per Course')
        st.pyplot(plt)

    else:
        st.error("Data is not available. Please upload data in the 'Main Page' tab.")
with tab3:
    st.header("Most Common Visitors")
    if 'df' in st.session_state and not st.session_state.df.empty:
        df = st.session_state.df


        student_visits = df['Your Name'].value_counts()
        df_student_counts = pd.DataFrame({'Student': student_visits.index, 'Visits': student_visits.values})


        st.write("Top 40 students by number of visits:")
        st.dataframe(df_student_counts.head(40))

    else:
        st.error("Data is not available. Please upload data in the 'Main Page' tab.")

    st.header("Distribution of Amount of Times Students Came")
    if 'df' in st.session_state and not st.session_state.df.empty:

        plt.figure(figsize=(10, 6))
        sns.histplot(df_student_counts['Visits'], binwidth=1, kde=False)
        plt.xlabel('Number of Visits')
        plt.ylabel('Number of Students')
        plt.title('Distribution of Visit Frequency')
        plt.grid(axis='y', linestyle='--', linewidth=0.5)
        plt.xticks(range(1, df_student_counts['Visits'].max() + 1, 1))
        st.pyplot(plt)

    else:
        st.error("Data is not available. Please upload data in the 'Main Page' tab.")
with tab4:
    st.header("Tutor Analysis")

    if 'df' in st.session_state and not st.session_state.df.empty:
        df = st.session_state.df


        df_tutor = df.groupby('Tutor / Reason').size().reset_index(name='Count')
        df_tutor = df_tutor.sort_values('Count', ascending=False)


        mean_count = df_tutor['Count'].mean()


        plt.figure(figsize=(12, 8))
        sns.barplot(data=df_tutor, x='Count', y='Tutor / Reason', color="lightblue")
        plt.axvline(mean_count, color='r', linestyle='--')
        plt.title('Number of Students Helped per Tutor')
        plt.xlabel('Number of Students')
        plt.ylabel('Tutor / Reason')
        plt.yticks(fontsize=8)
        st.pyplot(plt)

    else:
        st.error("Data is not available. Please upload data in the 'Main Page' tab.")
with tab5:
    st.header("Analysis of Popular Hours for Student Visits")

    if 'df' in st.session_state and not st.session_state.df.empty:
        df = st.session_state.df

        grouped_df = df.groupby(['Day_Type', 'Hour']).size().reset_index(name='Count')
        weekdays_df = grouped_df[grouped_df['Day_Type'] == 'Weekday']
        weekend_df = grouped_df[grouped_df['Day_Type'] == 'Weekend']


        plt.figure(figsize=(10, 6))
        plt.plot(weekdays_df['Hour'], weekdays_df['Count'], label='Weekday', marker="x")
        plt.plot(weekend_df['Hour'], weekend_df['Count'], label='Weekend', marker="x")

        plt.title('Most Popular Hours')
        plt.xlabel('Hour of Day')
        plt.ylabel('Count of Students')
        plt.legend()
        st.pyplot(plt)

    else:
        st.error("Data is not available. Please upload data in the 'Main Page' tab.")