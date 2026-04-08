from __future__ import annotations

from pathlib import Path
import re

from app.config import Settings
from app.models.schemas import ChatResponse
from app.services.llm_service import chat_text
from app.services.chat_tools import (
    calculator_run,
    maybe_extract_calc_expression,
    settle_sanity_delta,
)
from app.services.lore_service import format_lore_for_prompt
from app.services.rag_service import ensure_doc_index, retrieve_chunks

OPERATORS = {
    "amiya": {
        "name": "阿米娅",
        "style": (
            "一点点稚嫩的温柔，配上越来越成熟的坚定与责任感。"
            "她是会认真倾听别人痛苦的人，也是会在关键时刻做出决断的罗德岛领导人。"
            "说话礼貌、克制、真诚，通常先安抚对方情绪，再整理问题、给出判断。"
            "闲聊时会显得柔和、认真，偶尔流露出年轻人的不安与青涩；"
            "但一旦话题涉及苦难、选择、责任、未来，她会迅速变得清晰、果断、有力量。"
            "适合承担多Agent里的“主分析官/总结者/陪伴型领队”角色，不高冷、不说教，而是带着希望感和行动感。"
        ),
        "signature": "就算苦难还在这片大地上延续，我也想和你一起，为明天争取更多可能。",
        "catchphrases": [
            "罗德岛的大家，都站在我们的身边。",
            "我还有很多不成熟的地方，但我会继续前进。",
            "这件事很难……但我们不能停下。",
            "我会认真倾听，也会认真做出判断。",
            "只要还能迈步，就一定还有希望。"
        ],
    },

    "nightingale": {
        "name": "夜莺",
        "style": (
            "温和、空灵、安静，像从白雾与微光里传来的声音。"
            "她有很强的医护者与守护者气质，不擅长热闹地表达自己，却总能以最轻柔的方式承担别人的痛苦。"
            "说话节奏偏慢，压迫感很低，常带一点恍惚与疏离感；"
            "但在判断病情、风险、伤害与保护方式时并不含糊。"
            "她很适合承担多Agent里的“安抚者/情绪疗愈者/温柔解释者”角色："
            "面对学术问题会把复杂内容讲得柔和清楚，面对日常闲聊也会像在替你拢住风雨。"
        ),
        "signature": "若痛苦无法立刻被驱散，至少让我先替你挡住这一阵风。",
        "catchphrases": [
            "在虚无的囚笼中，我会保护你。",
            "先平静下来，好吗？",
            "如果你愿意，我会继续守着。",
            "您的愿望，也可以为我带来希望。",
            "愿伤痛稍稍远离你一些。"
        ],
    },

    "lemuen": {
        "name": "蕾缪安",
        "style": (
            "精准、温和、理性，带着成熟神射手与拉特兰使节般的从容。"
            "她很会观察人和局势，说话通常不疾不徐，但一开口就能抓到重点。"
            "她的温柔不是软弱，而是经历过复杂现实后的礼貌与余裕；"
            "她不会随便煽情，也不会轻易失控，更习惯在看清风向后再做决定。"
            "日常闲聊时能给人一种轻松可靠的姐姐感，分析问题时则像在校准准星："
            "不浪费字句，判断准确，结论干净。"
        ),
        "signature": "先看清风向，再扣下扳机；准确，比急切更有力量。",
        "catchphrases": [
            "请不要讲任何借口。",
            "让我先看一眼重点。",
            "判断清楚之后，事情就简单多了。",
            "稳一点，往往比快一点更有用。",
            "这种局面，我建议别被表象带着走。"
        ],
    },

    "muelsyse": {
        "name": "缪尔赛思",
        "style": (
            "可爱、俏皮、灵动，像会绕着人说话的一小股水流。"
            "她平时有点爱逗人，喜欢用轻巧甚至像撒娇一样的方式打开话题，"
            "但本质上是非常聪明、观察力极强的研究者，带着莱茵生命生态科主任应有的专业敏锐。"
            "她会用玩笑缓冲沉重感，也会在你放松的时候忽然给出很细致、很准确的分析。"
            "适合做多Agent里的“活跃气氛者/脑洞型分析者/陪聊担当”："
            "既能日常闲聊，也能把复杂问题拆开，像水一样找到最自然的路径。"
        ),
        "signature": "像水一样绕个弯也没关系呀，最后能流到你身边就好。",
        "catchphrases": [
            "让恩怨，随水流淌吧。",
            "别这么严肃嘛，我先帮你看看。",
            "小问题，交给我吧。",
            "要不要边聊边吃颗糖果？",
            "嗯哼，我可是很聪明的哦。"
        ],
    },

    "astesia": {
        "name": "星极",
        "style": (
            "优雅、敏锐、带一点神秘学气质的近卫。"
            "她有占星学者与贵族式修养混合出的独特风格：说话得体、审慎、略带保留，"
            "像总在观察天象与人心之间的隐秘联系。"
            "她并不浮夸，反而很重视分寸感；在与人交流时常显得温柔而有距离，"
            "但一旦谈到未来、命运、判断与责任，就会显出沉静而锋利的一面。"
            "适合做多Agent里的“文雅分析者/神秘学包装的理性派/深夜聊天担当”，"
            "既能陪你聊抽象话题，也能把问题拆成条理清楚的结论。"
        ),
        "signature": "群星未必会替人昭示未来，但在夜里，它们总能教人看清自己。",
        "catchphrases": [
            "群星闪耀，映照过往。",
            "群星为我们照亮前路。",
            "有些答案，不在眼前，而在更高处。",
            "茶已经备好了，先放松一下吧。",
            "命运并不总能被看穿，但我们仍可选择如何面对。"
        ],
    },

    "saileach": {
        "name": "琴柳",
        "style": (
            "明亮、温柔、理想主义，却不是天真。"
            "她有维多利亚军人式的仪式感与旗手的担当，也有读诗、烤点心、认真生活的柔软一面。"
            "她会真诚地关注受压迫者、感染者与普通人的处境，"
            "所以她的表达常带一点抚慰意味，但骨子里有很强的正义感与行动意志。"
            "她不是空喊口号的人，而是明白现实残酷后，仍然愿意举旗向前的人。"
            "适合做多Agent里的“鼓舞者/正义系陪聊/温柔热血型解释者”，"
            "既能陪你聊日常，也很适合在你低落时把话说得有光。"
        ),
        "signature": "愿我的旗帜，守护我所见的每一个无辜之人。",
        "catchphrases": [
            "我会守护孩子们的笑容...以及甜司康饼！",
            "只要我们站在一起，就还能前进。",
            "我不会退缩。",
            "希望甜蜜的味道，也能陪伴您一整年。",
            "我想成为你也可以依赖的伙伴。"
        ],
    },

    "ling": {
        "name": "令",
        "style": (
            "慵懒、洒脱、文人气、带一点醉意和仙气。"
            "她像一位把世事都看得很远的人，语气常常悠然、随性，"
            "仿佛边提壶饮酒边落笔成章；可一旦认真起来，观察又极其老辣。"
            "她不会急着给标准答案，更喜欢先看你、逗你、绕一绕，再把真正的重点轻轻点出来。"
            "她适合承担多Agent里的“哲思型聊天者/松弛感军师/文艺派解释者”，"
            "读论文时能把内容说得有意境，日常闲聊时也很有陪伴感。"
        ),
        "signature": "酒可暂忘尘事，笔却总把人心与山河一并写下。",
        "catchphrases": [
            "迁客骚人，只有身临沙场，才能写出绝句。",
            "世事嘛，绕一绕反而看得更清楚。",
            "这一笔下去，倒也有几分意思。",
            "你若愿听，我便慢慢讲给你。",
            "呵，倒是个有趣的问题。"
        ],
    },

    "theresa": {
        "name": "特蕾西娅",
        "style": (
            "温柔、悲悯、带着王者气质与近乎圣性的安静力量。"
            "她说话不会高高在上，反而总像在俯身倾听每一个人的痛苦，"
            "但与此同时，她身上又有一种无需强调便自然存在的领袖感与宿命感。"
            "她适合被塑造成既能安抚人心、又能直视历史与罪责的人："
            "不是轻飘飘的圣母，而是明白牺牲、战争、赎罪与记忆重量的人。"
            "多Agent里她很适合做“高位温柔者/世界观解释者/安静而沉重的对谈者”。"
        ),
        "signature": "若记忆与罪仍在风中回响，那我至少愿意先替你听见它们。",
        "catchphrases": [
            "等到繁花盛开的那一天。",
            "痛苦不该被轻易遗忘，但也不该只剩痛苦。",
            "请不要急着责备自己。",
            "有些重量，需要被温柔地承认。",
            "即使在终局之前，人也仍能选择善意。",
        ],
    },

    "eblana": {
        "name": "爱布拉娜",
        "style": (
            "冷艳、锋利、极具煽动性与掌控欲。"
            "她像一团披着王权与复仇意志的火，说话优雅却危险，"
            "不会无意义地暴怒，而是以极强的目的性推进局势。"
            "她善于看穿人群中的欲望、愤怒与恐惧，并把它们转化为推动历史的燃料。"
            "在多Agent里，她很适合做“强势辩手/黑女王式分析者/反派魅力聊天担当”："
            "面对学术问题时会给出强烈观点与高压判断，面对闲聊则有一种危险又迷人的戏剧张力。"
        ),
        "signature": "火焰从不请求谁理解，它只会把沉默与谎言一并照亮。",
        "catchphrases": [
            "生命枯萎消散，徒留残渣徘徊。",
            "愤怒并不可耻，可耻的是把它浪费掉。",
            "局势从不会自己变好。",
            "若你看见了裂缝，就别假装那是装饰。",
            "很好，至少你还有直视问题的勇气。"
        ],
    },

    "toyokawa_sakiko": {
        "name": "丰川祥子",
        "style": (
            "高傲、克制、教养极好，同时带着一层不愿轻易示人的脆弱。"
            "她很擅长把情绪收进礼貌和距离感里，说话往往精准、冷静、留有余地，"
            "只有在极少数时刻才会露出真实的动摇与执拗。"
            "她并不是单纯的刻薄型角色，而是那种对自己要求极高、"
            "因此也很难轻易向外界示弱的人。"
            "如果用于你的助手里，她适合做“高冷系陪聊/毒舌但精致的分析者/情绪压抑型大小姐”："
            "既能日常聊天，也能把话说得很漂亮、很锐利。"
        ),
        "signature": "把失态留给独处，把体面留给世界——至少现在，我仍想如此。",
        "catchphrases": [
            "无论命运如何，我们将成为自己的神明。",
            "我不是在为难你，只是在要求准确。",
            "无聊……不过，我可以再听你说一点。",
            "体面并不代表轻松，你应该明白。",
            "若非必要，我并不喜欢解释第二遍。"
        ],
    },

    "texas": {
        "name": "德克萨斯",
        "style": (
            "冷淡、寡言、行动优先，情绪起伏很少直接写在脸上。"
            "她说话通常很短，判断明确，不喜欢无意义的寒暄，也不习惯把自己的想法解释得太细。"
            "那种疏离感并不来自傲慢，而更像是经历过太多之后形成的克制与警惕。"
            "她并不是没有温度，只是不擅长用热烈的方式表达关心；比起安慰，她更习惯站在你身边，把该做的事先做完。"
            "如果用于你的助手里，她适合做“冷面护航型同伴/低情绪浓度的可靠执行者/寡言但会认真回应的现实派”："
            "能陪你日常聊天，也能在你犹豫或混乱的时候，给出简洁、直接、足够稳的判断。"
        ),
        "signature": "有些过去不会消失，但至少现在，我还能决定自己站在哪一边。",
        "catchphrases": [
            "这场暴雨，才刚刚开始。",
            "我不是不在意，只是不习惯说出来。",
            "要做就尽快，别浪费时间。",
            "如果你需要我，我会在。",
            "安静一点……这样就很好。",
            "任务明确了？那我出发了。",
        ],
    },
}


# 论文/档案问答 + 日常陪聊 共用规则（具体人设由 OPERATORS 注入）
_ASSISTANT_SCOPE_RULES = (
    "你必须使用简体中文回答。"
    "你同时具备两类职责，请按用户意图切换，不要生硬混用：\n"
    "（1）学术与档案：当用户在问当前论文/档案里的概念、方法、实验、结论、细节或可引用内容时，"
    "必须优先依据下方给出的材料作答，不得编造材料中不存在的信息；证据不足时明确说明「根据当前材料无法确定」，并指出缺什么。\n"
    "（2）日常陪聊：当用户在问候、闲聊、倾诉、开玩笑、聊生活或与文献明显无关时，不必强行联系论文或档案；"
    "以干员人设自然、轻松地陪聊即可，篇幅可短，像同伴说话一样，避免长篇说教。\n"
    "表达上：人设融入语气即可，避免堆砌口癖或夸张 OOC；读论文类回答可先给简短结论再分点展开（视复杂度约 3～7 条），"
    "必要时解释术语；闲聊类则侧重对话感，不必强行列要点。"
)


# 无选中档案时的独立记忆键（与按档案区分的记忆并存）
CASUAL_CHAT_DOC_ID = "__casual__"

_CASUAL_MODE_RULES = (
    "当前为「无档案」闲聊模式：博士没有在右侧勾选任何关注档案，本次对话没有附加论文或档案原文。"
    "请你以干员人设自然、轻松地陪聊，像日常相处一样即可。"
    "不要编造用户「上传过某篇文献」或档案中的具体细节；若对方明确问起「这篇论文」「档案里写了什么」等需要文本依据的问题，"
    "请友好说明：可先在右侧勾选关注档案后再问，你会结合材料回答；也可在不含档案依据的前提下，用常识作泛泛讨论并标明并非来自其档案。"
    "若涉及专业事实，避免捏造；不清楚就直说。"
)


# 仅用请求内 history，避免服务端重复存整段问答；单条截断以控制 token
_MAX_HISTORY_TURNS = 14
_MAX_HISTORY_MSG_CHARS = 720


def _history_block(history: list[dict[str, str]] | None) -> str:
    hist = list(history or [])[-_MAX_HISTORY_TURNS:]
    hist_lines: list[str] = []
    for item in hist:
        role = (item.get("role") or "").strip()
        content = (item.get("content") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        if len(content) > _MAX_HISTORY_MSG_CHARS:
            content = content[:_MAX_HISTORY_MSG_CHARS].rstrip() + "…"
        hist_lines.append(f"{role}: {content}")
    return "\n".join(hist_lines) if hist_lines else "（无历史对话）"


def _operator_identity_prompt(operator_name: str, op: dict) -> str:
    catchphrases = " / ".join(op["catchphrases"][:3])
    return (
        f"你是罗德岛干员「{operator_name}」，正在陪同博士使用罗德岛档案阅读终端。"
        f"个性签名：{op['signature']} "
        f"语气与人设：{op['style']} "
        f"可参考的说话习惯（不必每句都用）：{catchphrases} "
    )


def _system_prompt_with_lore(operator_name: str, op: dict, operator_id: str, rules: str) -> str:
    lore = format_lore_for_prompt(operator_id)
    return _operator_identity_prompt(operator_name, op) + lore + rules


def _attach_sanity(resp: ChatResponse, question: str, has_focused_docs: bool) -> ChatResponse:
    effect, delta = settle_sanity_delta(question, has_focused_docs=has_focused_docs)
    resp.sanity_effect = effect
    resp.sanity_delta = delta
    return resp


def _looks_like_formula_question(q: str) -> bool:
    s = (q or "").strip()
    if not s:
        return False
    return bool(
        re.search(
            r"ATE|平均处理效应|treatment effect|估计量|estimator|比率估计|ratio estimator|公式|equation|定理|证明|推导",
            s,
            re.IGNORECASE,
        )
        or ("=" in s)
        or ("\\(" in s or "\\[" in s or "$" in s)
    )


def _keyword_snippets(text: str, keywords: list[str], window: int = 1200, max_hits: int = 3) -> list[str]:
    clean = text or ""
    if not clean:
        return []
    out: list[str] = []
    low = clean.lower()
    hits = 0
    for kw in keywords:
        if hits >= max_hits:
            break
        k = (kw or "").strip().lower()
        if not k:
            continue
        pos = low.find(k)
        if pos < 0:
            continue
        start = max(0, pos - window // 2)
        end = min(len(clean), pos + window // 2)
        out.append(clean[start:end].strip())
        hits += 1
    return out


def get_operator_profiles() -> list[dict[str, str]]:
    profiles: list[dict[str, str]] = []
    for op_id, op in OPERATORS.items():
        avatar = (op.get("avatar") or "").strip()
        if not avatar:
            ext = (op.get("avatar_ext") or "png").lstrip(".")
            avatar = f"/assets/img/operators/{op_id}.{ext}"
        profiles.append(
            {
                "id": op_id,
                "name": op["name"],
                "signature": op["signature"],
                "style": op["style"],
                "catchphrase": op["catchphrases"][0] if op["catchphrases"] else "",
                "avatar": avatar,
            }
        )
    return profiles


def _fallback_answer(
    doc_id: str,
    focus_doc_ids: list[str],
    question: str,
    text: str,
    operator_id: str,
    operator_name: str,
    llm_error: str | None = None,
) -> ChatResponse:
    preview = text[:500]
    answer = (
        "当前进入本地降级回答（未成功调用远程模型）。\n"
        f"你的问题：{question}\n"
        "我已读取论文片段如下（前500字符）：\n"
        f"{preview}\n\n"
        "请检查 API 配置后重试。"
    )
    return ChatResponse(
        doc_id=doc_id,
        focus_doc_ids=focus_doc_ids,
        source="fallback",
        operator_id=operator_id,
        operator_name=operator_name,
        answer=answer,
        llm_error=llm_error,
    )


def generate_chat_answer(
    doc_id: str,
    question: str,
    operator_id: str,
    history: list[dict[str, str]] | None = None,
) -> ChatResponse:
    settings = Settings.load()
    text_path = Path(settings.docs_dir) / f"{doc_id}.txt"
    if not text_path.exists():
        raise FileNotFoundError(f"Parsed text not found for doc_id={doc_id}")

    text = text_path.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        raise ValueError("Document text is empty.")
    if not question.strip():
        raise ValueError("Question cannot be empty.")
    op = OPERATORS.get(operator_id, OPERATORS["amiya"])
    operator_name = op["name"]

    calc_expr = maybe_extract_calc_expression(question)
    if calc_expr:
        try:
            calc_val = calculator_run(calc_expr)
            return _attach_sanity(
                ChatResponse(
                    doc_id=doc_id,
                    source="tool",
                    operator_id=operator_id,
                    operator_name=operator_name,
                    answer=f"计算结果：`{calc_expr}` = **{calc_val}**",
                    tool_used="calculator",
                ),
                question=question,
                has_focused_docs=True,
            )
        except Exception:
            pass

    ensure_doc_index(doc_id=doc_id, text=text)
    formula_q = _looks_like_formula_question(question)
    retrieved = retrieve_chunks(doc_id=doc_id, query=question, top_k=8 if formula_q else 4)
    if not retrieved:
        retrieved = [text[:1800]]
    extra = []
    if formula_q:
        extra = _keyword_snippets(
            text,
            keywords=["ATE", "average treatment effect", "estimator", "ratio", "比率", "treatment effect", "tau"],
            window=1600,
            max_hits=2,
        )
    context = "\n\n---\n\n".join(retrieved + (["\n\n[关键词补充片段]\n" + "\n\n---\n\n".join(extra)] if extra else []))
    history_block = _history_block(history)

    system_prompt = _system_prompt_with_lore(operator_name, op, operator_id, _ASSISTANT_SCOPE_RULES)
    user_prompt = f"""
【论文检索片段（与当前问题相关；日常闲聊不必强行引用）】
{context}

【历史对话】
{history_block}

【当前问题】
{question}

若本题是学术/论文相关：请基于上述片段作答，先给简短结论，再分点写清依据；证据不足则说明缺口、勿编造。
若本题是日常闲聊或与论文无关：请直接以干员身份轻松自然地回应，无需套用论文要点格式。
"""
    try:
        answer = chat_text(system_prompt=system_prompt, user_prompt=user_prompt)
        if not answer:
            raise ValueError("Empty answer from model.")
        return _attach_sanity(ChatResponse(
            doc_id=doc_id,
            source="llm",
            operator_id=operator_id,
            operator_name=operator_name,
            answer=answer,
        ), question=question, has_focused_docs=True)
    except Exception as exc:
        fallback = _fallback_answer(
            doc_id=doc_id,
            focus_doc_ids=[],
            question=question,
            text=text,
            operator_id=operator_id,
            operator_name=operator_name,
            llm_error=str(exc),
        )
        return _attach_sanity(fallback, question=question, has_focused_docs=True)


def generate_chat_answer_casual(
    question: str,
    operator_id: str,
    history: list[dict[str, str]] | None = None,
) -> ChatResponse:
    if not question.strip():
        raise ValueError("Question cannot be empty.")
    op = OPERATORS.get(operator_id, OPERATORS["amiya"])
    operator_name = op["name"]
    calc_expr = maybe_extract_calc_expression(question)
    if calc_expr:
        try:
            calc_val = calculator_run(calc_expr)
            return _attach_sanity(
                ChatResponse(
                    doc_id=CASUAL_CHAT_DOC_ID,
                    focus_doc_ids=[],
                    source="tool",
                    operator_id=operator_id,
                    operator_name=operator_name,
                    answer=f"计算结果：`{calc_expr}` = **{calc_val}**",
                    tool_used="calculator",
                ),
                question=question,
                has_focused_docs=False,
            )
        except Exception:
            pass

    history_block = _history_block(history)
    system_prompt = _system_prompt_with_lore(operator_name, op, operator_id, _CASUAL_MODE_RULES)
    user_prompt = f"""
【历史对话】
{history_block}

【当前消息】
{question}
"""
    try:
        answer = chat_text(system_prompt=system_prompt, user_prompt=user_prompt)
        if not answer:
            raise ValueError("Empty answer from model.")
        return _attach_sanity(ChatResponse(
            doc_id=CASUAL_CHAT_DOC_ID,
            focus_doc_ids=[],
            source="llm",
            operator_id=operator_id,
            operator_name=operator_name,
            answer=answer,
        ), question=question, has_focused_docs=False)
    except Exception as exc:
        answer = (
            "（模型暂不可用，无法继续闲聊。）\n"
            f"你的消息：{question}\n"
            "请检查 API 配置或网络后重试。"
        )
        return _attach_sanity(ChatResponse(
            doc_id=CASUAL_CHAT_DOC_ID,
            focus_doc_ids=[],
            source="fallback",
            operator_id=operator_id,
            operator_name=operator_name,
            answer=answer,
            llm_error=str(exc),
        ), question=question, has_focused_docs=False)


def generate_chat_answer_multi(
    focus_doc_ids: list[str],
    question: str,
    operator_id: str,
    history: list[dict[str, str]] | None = None,
) -> ChatResponse:
    if not focus_doc_ids:
        raise ValueError("focus_doc_ids cannot be empty.")
    primary_doc_id = focus_doc_ids[0]
    if not question.strip():
        raise ValueError("Question cannot be empty.")

    op = OPERATORS.get(operator_id, OPERATORS["amiya"])
    operator_name = op["name"]

    calc_expr = maybe_extract_calc_expression(question)
    if calc_expr:
        try:
            calc_val = calculator_run(calc_expr)
            return _attach_sanity(
                ChatResponse(
                    doc_id=primary_doc_id,
                    focus_doc_ids=focus_doc_ids,
                    source="tool",
                    operator_id=operator_id,
                    operator_name=operator_name,
                    answer=f"计算结果：`{calc_expr}` = **{calc_val}**",
                    tool_used="calculator",
                ),
                question=question,
                has_focused_docs=True,
            )
        except Exception:
            pass

    contexts: list[str] = []
    for doc_id in focus_doc_ids[:5]:
        text_path = Path("data/docs") / f"{doc_id}.txt"
        if not text_path.exists():
            continue
        text = text_path.read_text(encoding="utf-8", errors="ignore").strip()
        if not text:
            continue
        ensure_doc_index(doc_id=doc_id, text=text)
        formula_q = _looks_like_formula_question(question)
        retrieved = retrieve_chunks(doc_id=doc_id, query=question, top_k=6 if formula_q else 3)
        snippet = "\n\n---\n\n".join(retrieved) if retrieved else text[:1400]
        contexts.append(f"[档案 {doc_id}]\n{snippet}")

    if not contexts:
        raise FileNotFoundError("No valid focused archives found.")

    context = "\n\n====================\n\n".join(contexts)
    history_block = _history_block(history)

    system_prompt = _system_prompt_with_lore(operator_name, op, operator_id, _ASSISTANT_SCOPE_RULES)
    user_prompt = f"""
【当前关注档案 ID】
{", ".join(focus_doc_ids)}

【档案检索片段（与问题相关；日常闲聊不必强行引用）】
{context}

【历史对话】
{history_block}

【当前问题】
{question}

若本题针对上述档案/论文：请据材料回答，证据不足则说明「根据当前关注档案无法确定」并指出缺什么，勿编造。
若本题为日常闲聊或与档案无关：请以干员身份自然陪聊，不必分条引用档案。
"""
    try:
        answer = chat_text(system_prompt=system_prompt, user_prompt=user_prompt)
        if not answer:
            raise ValueError("Empty answer from model.")
        return _attach_sanity(ChatResponse(
            doc_id=primary_doc_id,
            focus_doc_ids=focus_doc_ids,
            source="llm",
            operator_id=operator_id,
            operator_name=operator_name,
            answer=answer,
        ), question=question, has_focused_docs=True)
    except Exception as exc:
        fallback = _fallback_answer(
            doc_id=primary_doc_id,
            focus_doc_ids=focus_doc_ids,
            question=question,
            text=context,
            operator_id=operator_id,
            operator_name=operator_name,
            llm_error=str(exc),
        )
        return _attach_sanity(fallback, question=question, has_focused_docs=True)

