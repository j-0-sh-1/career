from pymongo import MongoClient
import streamlit as st

MONGO_URI = "mongodb+srv://joshuailangovansamuel:HHXm1xKAsKxZtQ6I@cluster0.pbvcd.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)

try:
    # The 'ping' command is a simple way to verify connection
    client.admin.command('ping')
    st.success("MongoDB is connected!")
except Exception as e:
    st.error(f"MongoDB connection error: {e}")
