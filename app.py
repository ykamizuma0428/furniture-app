import streamlit as st
import anthropic
import base64

st.set_page_config(
    page_title="家具セレクター",
    page_icon="🛋️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .main { background-color: #FAFAF8; }
    h1 { color: #1B4332; }
    h2, h3 { color: #2D6A4F; }
    .stButton>button {
        background-color: #2D6A4F;
        color: white;
        font-size: 18px;
        padding: 14px;
        border-radius: 10px;
        border: none;
        width: 100%;
        margin-top: 10px;
    }
    .stButton>button:hover { background-color: #1B4332; }
</style>
""", unsafe_allow_html=True)

# ─── パスワード保護 ───────────────────────────────────────────
def check_password():
    correct = st.secrets.get("APP_PASSWORD", "")
    if not correct:
        return True  # パスワード未設定なら通す（ローカル開発用）

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    st.title("🔐 家具セレクター")
    st.markdown("### パスワードを入力してください")
    pw = st.text_input("パスワード", type="password", placeholder="パスワードを入力")
    if st.button("ログイン"):
        if pw == correct:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("パスワードが違います")
    return False

if not check_password():
    st.stop()

# ─── APIキー（secretsから取得） ────────────────────────────────
api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
if not api_key:
    st.error("⚠️ APIキーが設定されていません。管理者に連絡してください")
    st.stop()

# ─── ヘッダー ────────────────────────────────────────────────
st.title("🛋️ 家具セレクター")
st.markdown("**間取り図と写真を見て、ぴったりの家具を提案します。**")
st.divider()

# ─── 画像アップロード ─────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📐 間取り図")
    floor_plan = st.file_uploader(
        "間取り図をアップロード",
        type=["jpg", "jpeg", "png"],
        help="部屋の形や広さが分かる間取り図をアップロードしてください",
    )
    if floor_plan:
        st.image(floor_plan, caption="アップロードした間取り図", use_container_width=True)

with col2:
    st.markdown("### 📸 部屋の写真（複数枚OK）")
    room_photos = st.file_uploader(
        "部屋の写真をアップロード",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        help="現在の部屋の様子が分かる写真。複数枚でもOKです",
    )
    if room_photos:
        preview_cols = st.columns(min(len(room_photos), 3))
        for i, photo in enumerate(room_photos[:3]):
            with preview_cols[i]:
                st.image(photo, use_container_width=True)
        if len(room_photos) > 3:
            st.caption(f"＋{len(room_photos) - 3}枚（最大3枚まで分析に使用されます）")

st.divider()

# ─── 予算・必需品 ─────────────────────────────────────────────
col3, col4 = st.columns(2)

with col3:
    st.markdown("### 💰 予算")
    budget = st.number_input(
        "合計予算（円）",
        min_value=10_000,
        max_value=5_000_000,
        value=300_000,
        step=10_000,
        format="%d",
    )
    st.caption(f"設定予算：**{budget:,}円**")

with col4:
    st.markdown("### 📝 必需品")
    must_haves = st.text_area(
        "絶対に欲しい家具・アイテム",
        placeholder="例：\n・ダブルベッド\n・大きめのテレビ台\n・作業できるデスク",
        height=130,
        help="必ず入れたい家具を自由に書いてください",
    )

st.divider()

# ─── 提案ボタン ───────────────────────────────────────────────
clicked = st.button("✨ 家具を提案してもらう", use_container_width=True)

if clicked:
    if not floor_plan and not room_photos:
        st.error("⚠️ 間取り図か部屋の写真を少なくとも1枚アップロードしてください。")
        st.stop()

    # 画像をBase64に変換
    content: list = []

    if floor_plan:
        data = base64.standard_b64encode(floor_plan.read()).decode()
        content += [
            {"type": "image", "source": {"type": "base64", "media_type": floor_plan.type or "image/jpeg", "data": data}},
            {"type": "text", "text": "↑ 間取り図"},
        ]

    for i, photo in enumerate(room_photos[:3]):
        data = base64.standard_b64encode(photo.read()).decode()
        content += [
            {"type": "image", "source": {"type": "base64", "media_type": photo.type or "image/jpeg", "data": data}},
            {"type": "text", "text": f"↑ 部屋の写真 {i + 1}"},
        ]

    needs = must_haves.strip() or "特になし"
    prompt = f"""あなたはプロのインテリアコーディネーターです。
アップロードされた間取り図と写真を分析して、最適な家具を提案してください。

## 条件
- 合計予算：{budget:,}円以内
- 必ず入れたい家具：{needs}

## 提案の形式（以下の構成で日本語で回答してください）

### 🏠 部屋の分析
間取りや写真から読み取ったこと（広さ、形、明るさ、雰囲気など）を簡単に説明してください。

### 🛋️ おすすめ家具リスト
各家具について：
- **家具の名前**
  - 予算目墉：〇〇円〜〇〇円
  - おすすめの理由（この部屋に合う理由）
  - 選ぶときのポイント
  - 参考ブランド（ニトリ・IKEA・無印良品など身近なお店）

### 💡 インテリアのアドバイス
色の合わせ方、配置のコツなど、実践的なアドバイスを3〜5個

### 💰 予算の振り分け案
| カテゴリ | 目安金額 |
|---|---|
| （例：ベッド） | 〇〇円 |
| **合計** | **{budget:,}円** |

専門用語は使わず、誰でも分かるやさしい言葉でお願いします。"""

    content.append({"type": "text", "text": prompt})

    with st.spinner("🔍 間取りと写真を分析しています…（30秒ほどかかることがあります）"):
        try:
            client = anthropic.Anthropic(api_key=api_key)
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                messages=[{"role": "user", "content": content}],
            )
            result = message.content[0].text
            st.success("✅ 提案が完成しました！")
            st.divider()
            st.markdown("## 🎯 あなたへの家具提案")
            st.markdown(result)

        except anthropic.AuthenticationError:
            st.error("❌ APIキーが正しくありません。")
        except Exception as e:
            st.error(f"❌ エラーが発生しました：{e}")
