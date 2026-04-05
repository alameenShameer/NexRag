@echo off
cd /d %~dp0\..\..
venv\Scripts\python.exe merge_kg.py
java -jar fuseki\apache-jena-fuseki-5.6.0\fuseki-server.jar --file=data/merged_kg.ttl /mesitam_kg
