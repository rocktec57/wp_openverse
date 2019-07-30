#!/bin/bash
CCCAPI_CONTAINER_NAME="${CCCAPI_CONTAINER_NAME:-cccatalog-api_web_1}"
ANALYTICS_CONTAINER_NAME="${ANALYTICS_CONTAINER_NAME:-cccatalog-api_analytics_1}"
# Set up API database and upstream
docker exec -ti $CCCAPI_CONTAINER_NAME /bin/bash -c 'python3 manage.py migrate --noinput'
docker exec -ti $ANALYTICS_CONTAINER_NAME /bin/bash -c 'PYTHONPATH=. pipenv run alembic upgrade head'
PGPASSWORD=deploy pg_dump -s -t image -U deploy -d openledger -h localhost -p 5432 | PGPASSWORD=deploy psql -U deploy -d openledger -p 5433 -h localhost
# Load sample data
PGPASSWORD=deploy psql -U deploy -d openledger -h localhost -p 5432 -c "INSERT INTO content_provider (created_on, provider_identifier, provider_name, domain_name, filter_content) VALUES (now(), 'flickr', 'Flickr', 'https://www.flickr.com', false), (now(), 'behance', 'Behance', 'https://www.behance.net', false);"
PGPASSWORD=deploy psql -U deploy -d openledger -h localhost -p 5433 -c "CREATE TABLE content_provider(provider_identifier varchar(50), provider_name varchar(250), created_on timestamp, domain_name varchar(500), filter_content boolean, notes text); INSERT INTO content_provider (created_on, provider_identifier, provider_name, domain_name, filter_content) VALUES (now(), 'flickr', 'Flickr', 'https://www.flickr.com', false), (now(), 'behance', 'Behance', 'https://www.behance.net', false);"
PGPASSWORD=deploy psql -U deploy -d openledger -h localhost -p 5433 -c "\copy image (id,created_on,updated_on,identifier,provider,source,foreign_identifier,foreign_landing_url,url,thumbnail,width,height,filesize,license,license_version,creator,creator_url,title,tags_list,last_synced_with_source,removed_from_source,meta_data,tags,watermarked,view_count) from 'sample_data.csv' with csv header"
# Load search quality assurance data.
curl -XPOST localhost:8001/task -H "Content-Type: application/json" -d '{"model": "image", "action": "LOAD_TEST_DATA"}'
# Ingest and index the data
curl -XPOST localhost:8001/task -H "Content-Type: application/json" -d '{"model": "image", "action": "INGEST_UPSTREAM"}'
