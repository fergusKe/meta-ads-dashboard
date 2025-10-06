import streamlit as st

from utils.experiments import register_experiment, record_result, list_experiments

st.set_page_config(page_title="A/B 測試控制台", page_icon="🧪", layout="wide")

st.title("🧪 A/B 測試控制台")
st.caption("建立並追蹤 Agent 版本的實驗")

with st.expander("建立新實驗", expanded=True):
    exp_name = st.text_input("實驗名稱")
    variant_a = st.text_area("Variant A 描述", value="CopywritingAgent v1")
    variant_b = st.text_area("Variant B 描述", value="CopywritingAgent v2")
    notes = st.text_area("備註", help="可以描述實驗目的或觀察指標")

    if st.button("建立實驗", type="primary"):
        if exp_name:
            register_experiment(exp_name, {"A": variant_a, "B": variant_b}, notes=notes)
            st.success("✅ 已建立實驗")
        else:
            st.error("請填寫實驗名稱")

st.divider()

st.subheader("📊 實驗列表")
experiments = list_experiments()
if not experiments:
    st.info("尚未建立任何實驗")
else:
    for experiment in experiments:
        with st.expander(experiment["name"], expanded=False):
            st.write("**Variants:**")
            for key, desc in experiment["variants"].items():
                st.markdown(f"- {key}: {desc}")

            st.write("**結果紀錄**")
            results = experiment.get("results", {})
            if results:
                st.json(results, expanded=False)
            else:
                st.info("尚未提交結果")

            st.write("**記錄數據**")
            metric_name = st.text_input(f"指標名稱 ({experiment['name']})", key=f"metric_{experiment['name']}")
            variant_key = st.selectbox(
                "Variant",
                options=list(experiment["variants"].keys()),
                key=f"variant_{experiment['name']}"
            )
            metric_value = st.number_input(
                "指標值",
                key=f"metric_value_{experiment['name']}",
            )
            if st.button("紀錄指標", key=f"record_{experiment['name']}"):
                if metric_name:
                    record_result(experiment['name'], variant_key, metric_name, metric_value)
                    st.success("指標已更新")
                else:
                    st.error("請輸入指標名稱")
