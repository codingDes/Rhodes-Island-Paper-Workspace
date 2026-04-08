from __future__ import annotations

import ast
import math
import operator
import random
import re

SANITY_MIN_STEP = 5
SANITY_MAX_STEP = 20

_REST_RE = re.compile(
    r"休息|歇歇|歇会|歇一下|累了|好累|好困|想睡|先睡|不(看|读|做)(了|啦)|"
    r"先这样|摸鱼|放松|不想动脑|不谈工作|不说论文|不说正事|换换脑子|"
    r"闲聊|聊点别的|下班|放工|喝口水|缓缓|拜拜|再见|溜了"
)
_SMALL_TALK_RE = re.compile(
    r"天气|降温|下雨|吃饭|午饭|晚饭|夜宵|周末|假期|游戏|番剧|动漫|电影|听歌|音乐|猫|狗|哈哈|嘿嘿"
)
_COGNITIVE_RE = re.compile(
    r"论文|文献|摘要|引言|结论|相关工作|实验|消融|数据集|引用|参考文献|"
    r"证明|定理|引理|命题|公理|推导|归纳|反证|"
    r"哲学|本体论|认识论|伦理|形而上学|自由意志|"
    r"数学|微积分|矩阵|线性代数|特征值|概率|统计|优化|图论|复杂度|"
    r"梯度|损失函数|反向传播|神经网络|深度学习|机器学习|transformer|attention|token|rag|"
    r"philosophy|epistemology|ontology|mathematics|theorem|lemma|proof|gradient|neural|arxiv",
    re.IGNORECASE,
)
_ASKING_RE = re.compile(r"为什么|如何理解|怎么证明|请解释|请分析|请推导|请对比|请总结|什么是")

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}
_FUNCS = {
    "abs": abs,
    "round": round,
    "max": max,
    "min": min,
    "sum": sum,
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "exp": math.exp,
    "pi": math.pi,
    "e": math.e,
}


def _is_rest(text: str) -> bool:
    t = text.strip()
    if not t:
        return False
    if _REST_RE.search(t):
        return True
    if len(t) <= 28 and re.fullmatch(r"(嗨|你好|哈喽|在吗|在不在|hi|hello)[\s！!。.?？～~]*", t, re.IGNORECASE):
        return True
    if re.fullmatch(r"(谢谢|辛苦了|收到|好的|嗯嗯|ok|okk)[\s！!。.?？～~]*", t, re.IGNORECASE):
        return True
    return False


def _is_small_talk(text: str) -> bool:
    return bool(_SMALL_TALK_RE.search(text))


def _is_cognitive(text: str) -> bool:
    if _COGNITIVE_RE.search(text):
        return True
    if _ASKING_RE.search(text) and len(text.strip()) > 12:
        return True
    if re.search(r"根据.*(材料|上文|档案|论文)|上面.*(文|段|节)", text):
        return True
    return False


def settle_sanity_delta(question: str, has_focused_docs: bool) -> tuple[str, int]:
    """
    返回 (effect, delta)，delta 为有符号值：
    - drain: 负数
    - restore: 正数
    """
    q = (question or "").strip()
    if _is_rest(q) or _is_small_talk(q):
        effect = "restore"
    elif _is_cognitive(q):
        effect = "drain"
    elif has_focused_docs:
        effect = "drain"
    else:
        effect = "restore"

    base = random.randint(SANITY_MIN_STEP, SANITY_MAX_STEP)
    length_bonus = min(12, len(q) // 35)
    if effect == "drain":
        return effect, -(base + length_bonus)

    low_sanity_bonus = random.randint(0, 6)
    long_chat_bonus = min(6, len(q) // 90)
    return effect, base + low_sanity_bonus + long_chat_bonus


def _eval_ast(node: ast.AST):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Num):
        return node.n
    if isinstance(node, ast.BinOp):
        if type(node.op) not in _OPS:
            raise ValueError("unsupported operator")
        return _OPS[type(node.op)](_eval_ast(node.left), _eval_ast(node.right))
    if isinstance(node, ast.UnaryOp):
        if type(node.op) not in _OPS:
            raise ValueError("unsupported unary operator")
        return _OPS[type(node.op)](_eval_ast(node.operand))
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("unsupported function call")
        name = node.func.id
        if name not in _FUNCS:
            raise ValueError(f"unsupported function: {name}")
        args = [_eval_ast(arg) for arg in node.args]
        return _FUNCS[name](*args)
    if isinstance(node, ast.Name):
        if node.id in _FUNCS:
            return _FUNCS[node.id]
        raise ValueError(f"undefined symbol: {node.id}")
    raise ValueError("unsupported expression")


def maybe_extract_calc_expression(question: str) -> str | None:
    q = (question or "").strip()
    if not q:
        return None
    q = re.sub(r"^(计算|算一下|帮我算|请计算|calculate)\s*", "", q, flags=re.IGNORECASE)
    q = re.sub(r"[=＝]\s*\??\s*$", "", q)
    q = q.replace(" ", "")
    if not re.fullmatch(r"[0-9\.\+\-\*\/\^\(\),a-zA-Z_]+", q):
        return None
    if not re.search(r"[\+\-\*\/\^]|sqrt|sin|cos|tan|log|exp|abs|round|max|min|sum", q, re.IGNORECASE):
        return None
    return q


def calculator_run(expression: str) -> str:
    expr = expression.replace("^", "**")
    node = ast.parse(expr, mode="eval")
    result = _eval_ast(node.body)
    return str(result)

