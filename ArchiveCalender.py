import streamlit as st
import calendar
from datetime import datetime, timedelta
import requests

# === 設定 ===
YOUTUBE_API_KEY = st.secrets["YOUTUBE_API_KEY"]
REACTIONS = ["🔥", "😢", "❤", "😂", "👏", "👍"]
MAX_VIDEOS_PER_DAY_IN_CALENDAR = 1 # カレンダーの各日に表示する最大の動画数

# --- YouTube API 呼び出し関数 ---
# (fetch_channels, fetch_videos, fetch_earliest_date 関数は変更なし)
def fetch_channels(query, max_results=5):
    params = {
        'key': YOUTUBE_API_KEY,
        'q': query,
        'type': 'channel',
        'part': 'snippet',
        'maxResults': max_results
    }
    try:
        response = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params=params
        )
        response.raise_for_status() 
        res_json = response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"APIリクエストエラー: {e}")
        return []
    except ValueError as e: 
        st.error(f"APIレスポンスのJSONデコードエラー: {e}")
        if 'response' in locals(): # responseオブジェクトが存在する場合のみraw textを表示
            st.error(f"API raw response: {response.text}")
        return []

    return [
        {
            'id': item['snippet']['channelId'],
            'title': item['snippet']['title']
        }
        for item in res_json.get('items', [])
    ]

def fetch_videos(channel_id, year, month, max_results=50):
    start = datetime(year, month, 1).isoformat("T") + "Z"
    end = (datetime(year, month, calendar.monthrange(year, month)[1]) + timedelta(days=1)).isoformat("T") + "Z"
    res = requests.get(
        "https://www.googleapis.com/youtube/v3/search",
        params={
            'key': YOUTUBE_API_KEY,
            'channelId': channel_id,
            'part': 'snippet',
            'order': 'date',
            'maxResults': max_results,
            'publishedAfter': start,
            'publishedBefore': end
        }
    ).json()
    return res.get('items', [])

def fetch_earliest_date(channel_id):
    res = requests.get(
        "https://www.googleapis.com/youtube/v3/search",
        params={
            'key': YOUTUBE_API_KEY,
            'channelId': channel_id,
            'part': 'snippet',
            'order': 'date',
            'maxResults': 1
        }
    ).json()
    items = res.get('items', [])
    if not items:
        return datetime.now()
    return datetime.fromisoformat(items[0]['snippet']['publishedAt'].replace("Z", "+00:00"))

# --- Streamlit UI ---
st.set_page_config(page_title="Vtuber アーカイブカレンダー", layout="wide")
st.title("📅 Vtuber アーカイブカレンダー")

# チャンネル検索 (変更なし)
st.header("🔍 Vtuberチャンネルを検索して選ぶ")
search_query = st.text_input("チャンネル名で検索", placeholder="例: 星街すいせい")
channel_id = None
if search_query:
    channels = fetch_channels(search_query)
    if not channels:
        st.warning("チャンネルが見つかりませんでした。別のキーワードを試してください。")
    else:
        options = [f"{c['title']} ({c['id']})" for c in channels]
        idx = st.selectbox("候補からチャンネルを選択", range(len(options)), format_func=lambda i: options[i])
        channel_id = channels[idx]['id']
        st.success(f"選択されたチャンネル: {channels[idx]['title']} (ID: {channel_id})")

# カレンダー表示
if channel_id:
    if 'year' not in st.session_state:
        st.session_state.year = datetime.now().year
    if 'month' not in st.session_state:
        st.session_state.month = datetime.now().month

    # 年月選択UI (変更なし)
    earliest_date = fetch_earliest_date(channel_id)
    current_date = datetime.now()
    year_options = list(range(2006, current_date.year + 1))
    if st.session_state.year not in year_options:
        st.session_state.year = year_options[-1]

    if st.session_state.year == current_date.year:
        month_options = list(range(1, current_date.month + 1))
    else:
        month_options = list(range(1, 13))

    if st.session_state.month not in month_options:
        st.session_state.month = month_options[0]

    nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 8]) # レイアウト比率を調整 ([2,1,7]などお好みで)
    with nav_col2:
        if st.button("◀ 前の月"):
            if st.session_state.month == 1:
                st.session_state.month = 12
                st.session_state.year -= 1
            else:
                st.session_state.month -= 1
    with nav_col1:
        selected_year = st.selectbox("年", year_options, index=year_options.index(st.session_state.year), key="year_select", format_func=str)
        st.session_state.year = selected_year

        selected_month = st.selectbox("月", month_options, index=month_options.index(st.session_state.month), key="month_select", format_func=str)
        st.session_state.month = selected_month
    with nav_col3:
        if st.button("次の月 ▶"):
            if st.session_state.month == 12:
                st.session_state.month = 1
                st.session_state.year += 1
            else:
                st.session_state.month += 1
    
    year = st.session_state.year
    month = st.session_state.month
    videos = fetch_videos(channel_id, year, month)

    day_map = {}
    for v in videos:
        dt = datetime.fromisoformat(v['snippet']['publishedAt'].replace("Z", "+00:00"))
        day_map.setdefault(dt.day, []).append(v)

    # --- ▼▼▼ ここからカレンダーの描画部分の修正 ▼▼▼ ---
    st.subheader(f"{year}年{month}月の配信カレンダー")
    
    # サムネイル等のスタイル調整 (任意)
    st.markdown("""
    <style>
    img { 
        max-height: 80px; /* サムネイルの高さを小さめに調整 */
        width: auto !important; 
        object-fit: contain; 
    }
    .stButton>button { /* ボタンの余白や文字サイズを少し小さくする */
        padding: 0.2rem 0.25rem;
        font-size: 0.75rem;
    }
    </style>
    """, unsafe_allow_html=True)

    cal = calendar.Calendar()
    for week in cal.monthdayscalendar(year, month):
        cols_week = st.columns(7)
        for i, day in enumerate(week):
            with cols_week[i]:
                if day == 0:
                    st.container().write(" ") # 空白の日の高さを確保するためコンテナを使う
                else:
                    date_button_label = f"{day}日"
                    videos_on_this_day = day_map.get(day, [])
                    num_videos_on_this_day = len(videos_on_this_day)

                    if num_videos_on_this_day > 0:
                         # 配信が1件より多い場合は件数を表示
                        if num_videos_on_this_day > MAX_VIDEOS_PER_DAY_IN_CALENDAR :
                             date_button_label += f" ({num_videos_on_this_day}件)"


                    # 日付ボタン (クリックでその日の配信一覧へ)
                    if st.button(date_button_label, key=f"cal_day_btn-{year}-{month}-{day}", use_container_width=True):
                        st.session_state['selected_day'] = day
                    
                    if videos_on_this_day:
                        for video_idx, v_data in enumerate(videos_on_this_day):
                            if video_idx >= MAX_VIDEOS_PER_DAY_IN_CALENDAR:
                                # 表示上限を超えた場合
                                if video_idx == MAX_VIDEOS_PER_DAY_IN_CALENDAR and num_videos_on_this_day > MAX_VIDEOS_PER_DAY_IN_CALENDAR:
                                    # 「もっと見る」的な表示は日付ボタンの件数表示で兼ねる
                                    # st.caption(f"他{num_videos_on_this_day - MAX_VIDEOS_PER_DAY_IN_CALENDAR}件...")
                                    pass
                                break # 上限に達したらこの日の動画表示は終了

                            # --- ここからMAX_VIDEOS_PER_DAY_IN_CALENDAR件までの動画情報を表示 ---
                            video_id = v_data['id'].get('videoId', f"{year}-{month}-{day}-{video_idx}")
                            thumbnail_url = v_data['snippet']['thumbnails'].get('default', {}).get('url', None)
                            
                            if thumbnail_url:
                                st.image(thumbnail_url, use_container_width=True)

                            # リアクション機能 (変更なし)
                            reaction_toggle_key = f"reaction_toggle_{video_id}"
                            if reaction_toggle_key not in st.session_state:
                                st.session_state[reaction_toggle_key] = False

                            if st.button("リアクション", key=f"toggle_btn_{video_id}", use_container_width=True):
                                st.session_state[reaction_toggle_key] = not st.session_state[reaction_toggle_key]

                               # リアクション絵文字の表示 (トグルがONの場合)
                            if st.session_state[reaction_toggle_key]:
                                reaction_cols = st.columns(len(REACTIONS))
                                for r_idx, emoji in enumerate(REACTIONS):
                                    with reaction_cols[r_idx]:
                                        if st.button(emoji, key=f"react_emoji_{video_id}_{emoji}", use_container_width=True):
                                            st.success(f"{v_data['snippet']['title']} に {emoji} でリアクションしました！")
                                            # TODO: ここにリアクションを保存・集計する処理を追加
                                            # st.session_state[reaction_toggle_key] = False # リアクション後は閉じる場合
                            # --- ここまで動画情報の表示 ---
                            
                    else: # 配信がない日
                        # st.write("配信なし") # 日付ボタンがあるので、"配信なし"は不要かもしれません
                        pass
    # --- ▲▲▲ ここまでカレンダーの描画部分の修正 ▲▲▲ ---

    # 選択された日の配信一覧表示 (変更なし)
    if 'selected_day' in st.session_state:
        sd = st.session_state.selected_day
        st.subheader(f"{year}年{month}月{sd}日の配信一覧")
        if sd in day_map:
            for v_data in day_map.get(sd, []): # day_map.get(sd, []) を使うとキーが存在しない場合もエラーにならない
                # 既存のコードを流用
                cols_detail = st.columns([1,3]) # カラム名を変更 (cols -> cols_detail)
                with cols_detail[0]:
                    thumb = v_data['snippet']['thumbnails'].get('medium', {}).get('url', None)
                    if thumb:
                        st.image(thumb, use_container_width=True)
                with cols_detail[1]:
                    title = v_data['snippet']['title']
                    desc = v_data['snippet']['description'][:200] + '...' if v_data['snippet']['description'] else ""
                    st.markdown(f"**{title}**")
                    st.caption(desc)
                    vid = v_data['id'].get('videoId')
                    if vid:
                        url = f"https://www.youtube.com/watch?v={vid}"
                        st.markdown(f"[▶️ YouTubeで観る]({url})")
                    # リアクションの集計（仮想カウント表示）
                    st.caption("リアクション: " + " ".join([f"{emoji} 0" for emoji in REACTIONS]))
        else:
            st.write("この日の配信はありません。")
