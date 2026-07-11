"""高齢者対話・見守りSNS(仮称)API — docs/REQUIREMENTS.md §8 準拠。"""
from typing import Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from . import config, consult, posts
from .llm import build_llm, detect_consent
from .schemas import ChatRequest, ChatResponse, Comment, CommentRequest, Post

app = FastAPI(title="caretech-hackathon API")
llm = build_llm()


@app.middleware("http")
async def no_cache_static(request, call_next):
    """更新した画面が古いキャッシュで出続けないよう、常に再検証させる。"""
    response = await call_next(request)
    if not request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-cache"
    return response

# セッション状態(ハッカソン規模のためインメモリ)
_histories: Dict[str, List[Dict]] = {}
_pending_posts: Dict[str, Dict] = {}  # session_id -> {"body": str, "display_name": str}


@app.get("/api/health")
def health() -> Dict:
    return {"ok": True, "llm": type(llm).__name__, "areas": consult.list_areas()}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    history = _histories.setdefault(req.session_id, [])

    # 投稿許可フロー(F6): 直前に投稿提案があれば、まず同意/拒否を判定する
    pending = _pending_posts.get(req.session_id)
    if pending:
        decision = detect_consent(req.text)
        if decision == "yes":
            del _pending_posts[req.session_id]
            posts.create_post(pending["display_name"], pending["body"])
            reply = "ありがとうございます。投稿しましたよ。若い人たちにも届くといいですね。"
            history.extend([{"role": "user", "content": req.text}, {"role": "assistant", "content": reply}])
            return ChatResponse(reply=reply, category="chat", posted=True)
        if decision == "no":
            del _pending_posts[req.session_id]
            reply = "分かりました。投稿はしないでおきますね。お話ししてくださってありがとうございます。"
            history.extend([{"role": "user", "content": req.text}, {"role": "assistant", "content": reply}])
            return ChatResponse(reply=reply, category="chat")
        # 同意でも拒否でもない発話は提案を保留したまま通常の対話として続ける

    result = llm.generate(history, req.text)
    category = result["category"]
    reply = result["reply"]

    consult_info = None
    if category == "consult":
        # 必須要件: 相談には必ず最寄り窓口を構造化データで添付する(F4)
        consult_info = consult.find_office(req.area)

    post_proposal = result.get("post_proposal")
    if category == "story" and post_proposal:
        _pending_posts[req.session_id] = {
            "body": post_proposal,
            "display_name": req.display_name,
        }

    history.extend([{"role": "user", "content": req.text}, {"role": "assistant", "content": reply}])
    return ChatResponse(
        reply=reply,
        category=category,
        consult_info=consult_info,
        post_proposal=post_proposal,
    )


@app.get("/api/posts", response_model=List[Post])
def get_posts() -> List[Post]:
    return posts.list_posts()


@app.post("/api/posts/{post_id}/like")
def like_post(post_id: str) -> Dict:
    likes = posts.like_post(post_id)
    if likes is None:
        raise HTTPException(status_code=404, detail="post not found")
    return {"likes": likes}


@app.post("/api/posts/{post_id}/comments", response_model=Comment)
def add_comment(post_id: str, req: CommentRequest) -> Comment:
    comment = posts.add_comment(post_id, req.name, req.body)
    if comment is None:
        raise HTTPException(status_code=404, detail="post not found")
    return comment


# フロントエンド(F7, F8): backend/static を配信
app.mount("/", StaticFiles(directory=str(config.STATIC_DIR), html=True), name="static")
