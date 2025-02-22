import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from pymongo import MongoClient
from sklearn.metrics.pairwise import cosine_similarity
import altair as alt

# ----- Custom CSS for a Modern Look & Button-like Options -----
st.markdown(
    """
    <link href="https://fonts.googleapis.com/css?family=Roboto&display=swap" rel="stylesheet">
    <style>
    /* Light theme */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa, #c3cfe2);
        font-family: 'Roboto', sans-serif;
        color: #343a40;
    }
    h1, h2, h3, h4, h5, h6, p, label {
        color: #343a40;
    }
    .stButton > button {
        border-radius: 10px;
        background-color: #007bff;
        color: white;
        padding: 10px 20px;
        border: none;
        font-size: 16px;
        transition: background-color 0.3s ease;
    }
    .stButton > button:hover {
        background-color: #0056b3;
    }
    /* Style radio options to appear in a row like buttons */
    div.row-widget.stRadio > div {
        flex-direction: row;
    }
    div.row-widget.stRadio > div > label {
        background: #e9ecef;
        padding: 8px 16px;
        margin-right: 10px;
        border-radius: 8px;
        cursor: pointer;
    }
    div.row-widget.stRadio > div > label:hover {
        background: #ced4da;
    }
    /* Dark mode override */
    @media (prefers-color-scheme: dark) {
      .stApp {
         background: linear-gradient(135deg, #232526, #414345);
         color: #ffffff;
      }
      h1, h2, h3, h4, h5, h6, p, label {
         color: #ffffff;
      }
      .stButton > button {
         background-color: #007bff !important;
         color: #ffffff !important;
      }
      .stButton > button:hover {
         background-color: #0056b3 !important;
      }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ----- MongoDB Connection -----
MONGO_URI = ("mongodb+srv://joshuailangovansamuel:HHXm1xKAsKxZtQ6I@"
             "cluster0.pbvcd.mongodb.net/career_recommendations?retryWrites=true&w=majority&appName=Cluster0")
client = MongoClient(MONGO_URI)
try:
    client.admin.command('ping')
    st.sidebar.success("MongoDB Connected!")
except Exception as e:
    st.sidebar.error("MongoDB connection error: " + str(e))
db = client["career_recommendations"]
submissions_collection = db["submissions"]

# ----- Load CSV Data -----
df = pd.read_csv("careers.csv")
# Assume numeric features are in columns 8–21 (0-indexed: 7 to 20)
numeric_cols = df.columns[7:21]

# ----- Mappings for Numeric Values -----
edu_mapping = {"High School": 0.3, "Bachelor's": 0.6, "Master's": 0.8, "PhD": 1.0}
skill_mapping = {"Beginner": 0.3, "Intermediate": 0.6, "Advanced": 0.9}
rating_mapping = {"Low": 0.3, "Moderate": 0.6, "High": 0.9}
personality_mapping = {"Disagree": 0.3, "Neutral": 0.6, "Agree": 0.9}

# ----- Keyword Extraction for Interests -----
# Assume the CSV column 'required_interests' contains comma-separated keywords.
def extract_keywords(series):
    keywords = set()
    for item in series.dropna():
        for word in item.split(","):
            keywords.add(word.strip().lower())
    return sorted(keywords)

interest_keywords = extract_keywords(df["required_interests"])

# ----- App Title and Tab Setup -----
st.title("Future-Ready Career Advisor")
tabs = st.tabs(["Input Form", "Show Careers Database"])

# ----- Input Form (All in One) -----
with tabs[0]:
    with st.form("career_form"):
        st.header("Step 1: Demographics")
        name = st.text_input("Full Name:")
        age = st.number_input("Age:", min_value=10, max_value=100, step=1)
        gender = st.radio("Gender:", options=["Male", "Female", "Other"])
        primary_field = st.radio("Primary Field of Interest:", 
                                  options=["Technology", "Design", "Management", "Healthcare", "Other"])
        secondary_field = st.radio("Secondary Field of Interest:", 
                                    options=["Technology", "Design", "Management", "Healthcare", "Other"])
        
        st.header("Step 2: Skills & Interests")
        st.subheader("Skills & Education")
        education = st.radio("Highest Level of Education:", options=list(edu_mapping.keys()))
        technical = st.radio("Technical Skills:", options=list(skill_mapping.keys()))
        analytical = st.radio("Analytical Skills:", options=list(skill_mapping.keys()))
        communication = st.radio("Communication Skills:", options=list(skill_mapping.keys()))
        st.subheader("Interests")
        creativity = st.radio("Creativity:", options=list(rating_mapping.keys()))
        adaptability = st.radio("Adaptability:", options=list(rating_mapping.keys()))
        interest_tech = st.radio("Interest in Technology:", options=list(rating_mapping.keys()))
        interest_design = st.radio("Interest in Design:", options=list(rating_mapping.keys()))
        interest_management = st.radio("Interest in Management:", options=list(rating_mapping.keys()))
        
        st.header("Step 3: Personality Test")
        st.write("Indicate your agreement with each statement:")
        q1 = st.radio("I enjoy exploring new ideas and experiences.", options=list(personality_mapping.keys()))
        q2 = st.radio("I am organized and detail-oriented.", options=list(personality_mapping.keys()))
        q3 = st.radio("I feel energized when interacting with others.", options=list(personality_mapping.keys()))
        q4 = st.radio("I prefer cooperation over competition.", options=list(personality_mapping.keys()))
        q5 = st.radio("I often feel stressed in challenging situations.", options=list(personality_mapping.keys()))
        
        st.header("Step 4: Keyword Interests")
        st.write("Select the keywords that best represent your interests (you can select multiple):")
        selected_keywords = st.multiselect("Your Interests:", options=interest_keywords, default=[])
        
        submitted = st.form_submit_button("Submit and Get Recommendations")
        
    # ----- Process the Submission -----
    if submitted:
        # Build the 14-dimensional numeric vector (from Steps 2 and 3)
        user_numeric_vector = [
            skill_mapping[technical],        # technical_skills
            skill_mapping[analytical],         # analytical_skills
            skill_mapping[communication],      # communication_skills
            rating_mapping[creativity],        # creativity
            rating_mapping[adaptability],      # adaptability
            edu_mapping[education],            # education_level
            rating_mapping[interest_tech],     # interest_in_tech
            rating_mapping[interest_design],   # interest_in_design
            rating_mapping[interest_management],# interest_in_management
            personality_mapping[q1],           # openness
            personality_mapping[q2],           # conscientiousness
            personality_mapping[q3],           # extraversion
            personality_mapping[q4],           # agreeableness
            personality_mapping[q5]            # neuroticism
        ]
        
        # Build the full submission record (including keyword interests)
        submission_record = {
            "name": name,
            "age": age,
            "gender": gender,
            "primary_field": primary_field,
            "secondary_field": secondary_field,
            "education": education,
            "technical": technical,
            "analytical": analytical,
            "communication": communication,
            "creativity": creativity,
            "adaptability": adaptability,
            "interest_tech": interest_tech,
            "interest_design": interest_design,
            "interest_management": interest_management,
            "personality": {
                "exploring_new_ideas": q1,
                "organized": q2,
                "social_interaction": q3,
                "cooperative": q4,
                "stress_response": q5
            },
            "keyword_interests": selected_keywords,
            "user_numeric_vector": user_numeric_vector,
            "timestamp": datetime.utcnow()
        }
        submissions_collection.insert_one(submission_record)
        
        # ----- Compute Numeric Similarity -----
        user_vec = np.array(user_numeric_vector).reshape(1, -1)
        career_numeric_vectors = df[numeric_cols].values.astype(float)
        numeric_sim = cosine_similarity(user_vec, career_numeric_vectors)[0]
        
        # ----- Compute Keyword Similarity (Jaccard Similarity) -----
        # Assume the "required_interests" field in the CSV contains comma-separated keywords.
        def jaccard_similarity(user_set, career_str):
            career_keywords = {kw.strip().lower() for kw in career_str.split(",")} if pd.notnull(career_str) else set()
            if not user_set and not career_keywords:
                return 1.0
            if not user_set or not career_keywords:
                return 0.0
            intersection = user_set.intersection(career_keywords)
            union = user_set.union(career_keywords)
            return len(intersection) / len(union)
        
        user_keyword_set = {kw.lower() for kw in selected_keywords}
        keyword_sim = df["required_interests"].apply(lambda x: jaccard_similarity(user_keyword_set, x) if pd.notnull(x) else 0.0).values
        
        # ----- Combine Similarities (Weights can be tuned) -----
        # For example: 60% numeric, 40% keyword similarity.
        combined_sim = 0.6 * numeric_sim + 0.4 * keyword_sim
        df["combined_similarity"] = combined_sim
        top_matches = df.sort_values(by="combined_similarity", ascending=False).head(5)
        
        # ----- Display Recommendations -----
        st.markdown("## Career Recommendations")
        for idx, row in top_matches.iterrows():
            with st.container():
                st.markdown(f"### {row['career']}")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Annual Average Income:** {row['annual_average_income']}")
                    st.write(f"**Job Demands:** {row['job_demands']}")
                    st.write(f"**Job Description:** {row['job_description']}")
                with col2:
                    st.write(f"**Required Skills:** {row['required_skills']}")
                    st.write(f"**Required Interests:** {row['required_interests']}")
                    st.write(f"**Personality Fit:** {row['personality_fit']}")
                st.write(f"**Combined Similarity Score:** {row['combined_similarity']:.2f}")
                st.markdown("---")
        
        # ----- Visualization: Horizontal Bar Chart of Numeric Profile -----
        metrics = ["Technical", "Analytical", "Communication", "Creativity", "Adaptability",
                   "Education", "Interest Tech", "Interest Design", "Interest Management",
                   "Openness", "Conscientiousness", "Extraversion", "Agreeableness", "Neuroticism"]
        viz_df = pd.DataFrame({"Metric": metrics, "Score": user_numeric_vector})
        chart = alt.Chart(viz_df).mark_bar().encode(
            x=alt.X("Score:Q", scale=alt.Scale(domain=[0, 1])),
            y=alt.Y("Metric:N", sort="-x"),
            tooltip=["Metric", "Score"]
        ).properties(
            width=600,
            height=400,
            title="Your Numeric Profile Metrics"
        )
        st.altair_chart(chart, use_container_width=True)
        
        # ----- Sidebar Notification: Latest Submission Info -----
        latest_submission = list(submissions_collection.find().sort("timestamp", -1).limit(1))
        if latest_submission:
            latest = latest_submission[0]
            st.sidebar.markdown("### Latest Submission")
            st.sidebar.write(f"User: {latest.get('name', 'N/A')}")
            ts = latest.get("timestamp", datetime.utcnow())
            st.sidebar.write(f"Submitted at: {ts.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            st.sidebar.write("No submissions yet.")

# ----- Show Full Careers Database Tab -----
with tabs[1]:
    st.header("Careers Database")
    if st.button("Show Full Database"):
        st.dataframe(df)
