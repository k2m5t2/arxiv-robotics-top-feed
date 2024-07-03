# basics
import requests
from datetime import datetime, timedelta
import time
# server
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
# data
from arxiv import Client, Search, SortCriterion
# caching
# import sqlite3
from persistent_dict import PersistentDict

PRUNE = True

app = FastAPI()
client = Client()

# cache = {} # map title to: S2id, citationCount, etc. key is paper title.
cache = PersistentDict() # map title to: S2id, citationCount, etc. key is paper title.

def search_semantic_scholar(title, author=None, api_key=None):
    url = 'https://api.semanticscholar.org/graph/v1/paper/search'
    query = title
    if author:
        query += f" {author}"

    params = {
        'query': query,
        # 'fields': 'title,authors,externalIds,corpusId',
        'fields': 'title,authors,externalIds,corpusId,citationCount',
        'limit': 1
    }

    # headers = {}
    # if api_key:
    #     headers['x-api-key'] = api_key

    # response = requests.get(url, params=params, headers=headers)
    response = requests.get(url, params=params)
    data = response.json()

    if 'data' in data and len(data['data']) > 0:
        paper = data['data'][0]
        return paper

    return None

def search_arxiv_by_date_range(query, start_date, end_date, sort_by="citations", limit=50):
    # Format the date for arXiv search
    start_date_str = (start_date + timedelta(days=-1)).strftime('%Y%m%d')
    end_date_str = end_date.strftime('%Y%m%d')

    # Create a search query with the date filter
    # search_query = f"{query} AND submittedDate:[{formatted_date} TO {formatted_date}]"
    search_query = f"{query} AND submittedDate:[{start_date_str} TO {end_date_str}]"

    # Perform the search
    search = Search(
        query=search_query,
        max_results=100,
        sort_by=SortCriterion.SubmittedDate
    )

    # Iterate over the results
    results = []
    for result in client.results(search):
        results.append(result)

    # TODO instead of using richer_results, turn arxiv.Result into Python dicts
    #      and add citationCount as well as s2id when returning data to frontend!

    # TODO sort by citations, or any other condition
    if sort_by == "citations":
        richer_results = []

        for result in results:
            title = result.title
            if title in cache:
                paper = cache[title]
                richer_result = {"citationCount": paper['citationCount'], "s2id": paper['s2id'], "result": result}
            else:
                s2paper = search_semantic_scholar(title)
                if s2paper is None: continue
                richer_result = {"citationCount": s2paper['citationCount'], "s2id": s2paper['corpusId'], "result": result}
                cache[title] = { "result": result, "citationCount": s2paper['citationCount'], "s2id": s2paper['corpusId']}
                time.sleep(0.5)

            richer_results.append((richer_result))

        # NOTE v1: doesn't return citationCount to frontend
        # sorted_richer_results = sorted(richer_results, key=lambda x: x['citationCount'], reverse=True)
        # sorted_results = [richer_result["result"] for richer_result in sorted_richer_results]
        # results = sorted_results

        # NOTE v2: returns citationCount to frontend but a lil hacky
        sorted_richer_results = sorted(richer_results, key=lambda x: x['citationCount'], reverse=True)
        sorted_results = []
        for richer_result in sorted_richer_results[:limit]:
            result_dict = dict(richer_result["result"]._raw)
            result_dict["citationCount"] = richer_result["citationCount"]
            result_dict["s2id"] = richer_result["s2id"]
            if PRUNE:
                del result_dict["summary"]
                del result_dict["summary_detail"]
                del result_dict["updated_parsed"]
                del result_dict["published_parsed"]
                del result_dict["title_detail"]
                del result_dict["author_detail"]
                del result_dict["links"]
                del result_dict["authors"] # a bit extreme
                del result_dict["tags"] # a bit extreme
            sorted_results.append(result_dict)
        results = sorted_results

    elif sort_by == "recency":
        sorted_results = sorted(results, key=lambda x: x.published.date())
        results = sorted_results[:limit]

    return results[:limit]

@app.get("/papers")
def get_papers(category, start_date_str, end_date_str, sort_by="citations", limit: int = 30):
    # TODO pack into a reasonable data structure (unless there's no need and can be serialized into JSON already!?)
    start_date = datetime.fromisoformat(start_date_str).date()
    end_date = datetime.fromisoformat(end_date_str).date()
    results = search_arxiv_by_date_range(f"cat:{category}", start_date, end_date, sort_by, limit)
    return results

@app.on_event("shutdown")
def shutdown_event():
    cache.save()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def main():
    uvicorn.run(app, port="8000")

if __name__ == "__main__":
    main()
