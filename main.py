import os

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from tinydb import TinyDB, Query as TinyQuery
from difflib import SequenceMatcher
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["arcwiki.mcd.blue", "localhost"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://arcwiki.mcd.blue",
        "https://arcwiki.mcd.blue",
        "http://localhost",
        "http://127.0.0.1"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = TinyDB(os.path.join('data', 'sentences.json'))

class Sentence(BaseModel):
    title: str
    context: str

def calculate_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

@app.get("/page/{title}")
async def get_sentence(title: str, context: str = Query(None)):
    SentenceQuery = TinyQuery()
    sentence = db.get(SentenceQuery.title == title)
    if sentence:
        if context is not None:
            if sentence['context'] == "" or context == "":
                if context != "":
                    db.update({"context": context}, SentenceQuery.title == title)
                return {"title": title, "context": sentence['context'], "likes": sentence['likes']}
            similarity = calculate_similarity(sentence['context'], context)
            if similarity < 0.5:
                db.update({"context": context, "likes": 0}, SentenceQuery.title == title)
                return {"title": title, "context": context, "likes": 0, "message": "一句话内容变化超过一半，已视为新内容并重置点赞数。"}
        return {"title": sentence['title'], "context": sentence['context'], "likes": sentence['likes']}
    else:
        db.insert({"title": title, "context": context if context is not None else "", "likes": 0})
        return {"title": title, "context": context if context is not None else "", "likes": 0, "message": "一句话不存在，已创建新内容，点赞数为0。"}

@app.post("/page/{title}/like")
async def like_sentence(title: str):
    SentenceQuery = TinyQuery()
    sentence = db.get(SentenceQuery.title == title)
    if sentence:
        new_likes = sentence['likes'] + 1
        db.update({"likes": new_likes}, SentenceQuery.title == title)
        return {"message": "点赞成功。", "likes": new_likes}
    else:
        raise HTTPException(status_code=404, detail="一句话未找到。")

@app.post("/page/{title}/unlike")
async def unlike_sentence(title: str):
    SentenceQuery = TinyQuery()
    sentence = db.get(SentenceQuery.title == title)
    if sentence:
        if sentence['likes'] > 0:
            new_likes = sentence['likes'] - 1
            db.update({"likes": new_likes}, SentenceQuery.title == title)
            return {"message": "取消点赞成功。", "likes": new_likes}
        else:
            return {"message": "点赞数已为0，无法继续取消点赞。", "likes": 0}
    else:
        raise HTTPException(status_code=404, detail="一句话未找到。")


@app.delete("/page/{title}")
async def delete_sentence(title: str):
    SentenceQuery = TinyQuery()
    sentence = db.get(SentenceQuery.title == title)
    if sentence:
        db.remove(SentenceQuery.title == title)
        return {"message": "一句话已删除。"}
    else:
        raise HTTPException(status_code=404, detail="一句话未找到。")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
