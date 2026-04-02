@echo off
echo Starting Fuseki Server...
echo dataset: /mesitam_kg
echo Source: data/mesitam_data.ttl
java -jar fuseki\apache-jena-fuseki-5.6.0\fuseki-server.jar --file=data/mesitam_data.ttl /mesitam_kg
pause
