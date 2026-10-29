import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="카드콕 | 신용카드 추천", page_icon="💳", layout="centered")

CATEGORIES = ["마트", "편의점", "주유", "외식", "온라인 쇼핑", "교통", "카페", "통신", "기타"]

if "rules" not in st.session_state:
    st.session_state.rules = []
if "history" not in st.session_state:
    st.session_state.history = []

st.title("💳 카드콕")
st.caption("결제 전에, 내 카드 중 가장 유리한 카드를 찾아보세요.")
st.info("초기 버전입니다. 카드 혜택은 사용자가 직접 입력하며, 실제 카드 약관과 청구 내역을 확인해야 합니다.")

tab_recommend, tab_add, tab_manage, tab_history = st.tabs(
    ["카드 추천", "혜택 등록", "등록 혜택 관리", "결제 기록"]
)

with tab_recommend:
    st.subheader("어디에서 얼마를 결제하시나요?")
    category = st.selectbox("결제 업종", CATEGORIES, key="purchase_category")
    amount = st.number_input("결제 예정 금액 (원)", min_value=0, value=30000, step=1000, key="purchase_amount")
    if st.button("가장 유리한 카드 찾기", type="primary", use_container_width=True):
        candidates = []
        for idx, rule in enumerate(st.session_state.rules):
            if rule["category"] != category:
                continue
            if amount <= 0:
                continue
            eligible = amount >= rule["min_spend"]
            remaining = max(0, rule["monthly_cap"] - rule["used_cap"])
            reward = min(amount * rule["rate"] / 100, remaining) if eligible else 0
            candidates.append({
                "idx": idx,
                "카드": rule["card"],
                "업종": rule["category"],
                "예상 혜택": int(reward),
                "혜택률": f'{rule["rate"]:g}%',
                "남은 월 한도": int(remaining),
                "전월 실적 조건": f'{rule["min_spend"]:,}원 결제 기준',
                "조건 충족": "충족" if eligible else "미충족"
            })
        st.session_state.last_candidates = candidates
        st.session_state.last_category = category
        st.session_state.last_amount = amount

    if "last_candidates" in st.session_state:
        candidates = st.session_state.last_candidates
        if not candidates:
            st.warning(f"'{st.session_state.last_category}' 업종에 등록된 혜택이 없습니다. '혜택 등록' 탭에서 카드를 등록해 주세요.")
        else:
            ranked = sorted(candidates, key=lambda x: (x["예상 혜택"], x["남은 월 한도"]), reverse=True)
            best = ranked[0]
            if best["예상 혜택"] <= 0:
                st.warning("현재 등록 정보 기준으로 적용 가능한 혜택이 없습니다. 실적 조건과 남은 한도를 확인하세요.")
            else:
                st.success(f'추천 카드: **{best["카드"]}** · 예상 혜택 약 **{best["예상 혜택"]:,}원**')
            st.dataframe(pd.DataFrame(ranked).drop(columns=["idx"]), use_container_width=True, hide_index=True)
            st.caption("예상 혜택은 입력한 할인·적립률과 남은 월 한도를 기준으로 계산한 값입니다. 포인트 가치, 제외 가맹점, 결제 방식 등은 반영하지 않습니다.")
            options = [f'{x["카드"]} ({x["예상 혜택"]:,}원 예상)' for x in ranked]
            chosen = st.selectbox("실제로 결제한 카드 선택", options, key="chosen_card")
            if st.button("결제 기록 저장 및 한도 반영", use_container_width=True):
                selected = ranked[options.index(chosen)]
                idx = selected["idx"]
                rule = st.session_state.rules[idx]
                applied = min(st.session_state.last_amount * rule["rate"] / 100, max(0, rule["monthly_cap"] - rule["used_cap"])) if st.session_state.last_amount >= rule["min_spend"] else 0
                rule["used_cap"] = min(rule["monthly_cap"], rule["used_cap"] + applied)
                st.session_state.history.append({
                    "날짜": str(date.today()),
                    "업종": st.session_state.last_category,
                    "결제 금액": int(st.session_state.last_amount),
                    "카드": rule["card"],
                    "예상 혜택": int(applied)
                })
                st.session_state.rules[idx] = rule
                st.success(f"결제 기록을 저장했습니다. 예상 혜택 {int(applied):,}원을 이번 달 사용 한도에 반영했습니다.")

with tab_add:
    st.subheader("카드 혜택 등록")
    st.write("카드 한 장에 여러 업종 혜택이 있으면 업종별로 각각 등록하세요.")
    with st.form("add_rule_form", clear_on_submit=True):
        card = st.text_input("카드 이름", placeholder="예: OO카드")
        cat = st.selectbox("혜택 적용 업종", CATEGORIES, key="new_category")
        rate = st.number_input("할인 또는 적립률 (%)", min_value=0.0, max_value=100.0, value=5.0, step=0.5)
        cap = st.number_input("월 최대 혜택 한도 (원)", min_value=0, value=10000, step=1000)
        used = st.number_input("이번 달 이미 사용한 혜택 (원)", min_value=0, value=0, step=500)
        min_spend = st.number_input("혜택 적용을 위한 최소 결제금액 (원)", min_value=0, value=0, step=1000)
        submitted = st.form_submit_button("혜택 등록", type="primary", use_container_width=True)
        if submitted:
            if not card.strip():
                st.error("카드 이름을 입력해 주세요.")
            elif used > cap:
                st.error("이번 달 사용한 혜택은 월 최대 한도보다 클 수 없습니다.")
            else:
                st.session_state.rules.append({
                    "card": card.strip(), "category": cat, "rate": float(rate),
                    "monthly_cap": int(cap), "used_cap": int(used), "min_spend": int(min_spend)
                })
                st.success(f"{card.strip()}의 {cat} 혜택을 등록했습니다.")

with tab_manage:
    st.subheader("등록된 혜택과 남은 한도")
    if not st.session_state.rules:
        st.write("아직 등록된 혜택이 없습니다.")
    else:
        rows = []
        for i, r in enumerate(st.session_state.rules):
            rows.append({
                "번호": i + 1, "카드": r["card"], "업종": r["category"],
                "혜택률": f'{r["rate"]:g}%', "월 최대 혜택": r["monthly_cap"],
                "이번 달 사용": r["used_cap"],
                "남은 한도": max(0, r["monthly_cap"] - r["used_cap"]),
                "최소 결제금액": r["min_spend"]
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        remove_idx = st.selectbox("삭제할 혜택 선택", range(len(st.session_state.rules)),
                                  format_func=lambda i: f'{st.session_state.rules[i]["card"]} / {st.session_state.rules[i]["category"]}')
        if st.button("선택한 혜택 삭제", use_container_width=True):
            removed = st.session_state.rules.pop(remove_idx)
            st.success(f'{removed["card"]} / {removed["category"]} 혜택을 삭제했습니다.')
        st.download_button(
            "혜택 데이터 CSV로 내려받기",
            data=pd.DataFrame(st.session_state.rules).to_csv(index=False).encode("utf-8-sig"),
            file_name="card_benefit_rules.csv",
            mime="text/csv",
            use_container_width=True
        )
        uploaded = st.file_uploader("이전에 내려받은 혜택 CSV 불러오기", type=["csv"])
        if uploaded is not None and st.button("CSV 불러오기"):
            try:
                df = pd.read_csv(uploaded)
                required = {"card", "category", "rate", "monthly_cap", "used_cap", "min_spend"}
                if not required.issubset(set(df.columns)):
                    st.error("CSV 형식이 올바르지 않습니다.")
                else:
                    st.session_state.rules = df[list(required)].to_dict("records")
                    st.success("혜택 데이터를 불러왔습니다.")
                    st.rerun()
            except Exception as e:
                st.error(f"CSV를 읽을 수 없습니다: {e}")

with tab_history:
    st.subheader("결제 기록")
    if st.session_state.history:
        df = pd.DataFrame(st.session_state.history)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("결제 기록 CSV 내려받기", df.to_csv(index=False).encode("utf-8-sig"),
                           "card_payment_history.csv", "text/csv", use_container_width=True)
    else:
        st.write("아직 결제 기록이 없습니다.")

st.divider()
st.caption("개인정보·카드번호·비밀번호를 입력하지 마세요. 이 앱은 금융사 계정에 연결되지 않으며, 기본 버전의 데이터는 앱 세션이 종료되면 사라질 수 있습니다. CSV로 백업해 주세요.")
