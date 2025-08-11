import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from collections import Counter
import os
import time
from openai import OpenAI
import io
import json

# 環境変数からOpenAIのAPIキーを取得
client = OpenAI(api_key="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")

if client is None:
    raise ValueError("APIキーが設定されていません。環境変数 'OPENAI_API_KEY' を設定してください。")

# matplotlibで日本語フォントを設定
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.sans-serif'] = ['Hiragino Sans', 'Yu Gothic', 'Meiryo', 'Takao', 'IPAexGothic', 'IPAPGothic', 'VL PGothic', 'Noto Sans CJK JP']

# データファイルのパス
DATA_FILE = 'todo_list.csv'
ASSIGNEE_FILE = 'assignee_list.csv'  # 担当者リスト用ファイル


# 担当者リストの読み込み
def load_assignee_list():
    if os.path.exists(ASSIGNEE_FILE):
        try:
            df_assignees = pd.read_csv(ASSIGNEE_FILE)
            return df_assignees['担当者名'].tolist()
        except:
            # ファイルが壊れている場合の初期化
            initial_assignees = ['渡邉 祥太', 'hoge', 'fuga']
            save_assignee_list(initial_assignees)
            return initial_assignees
    else:
        # 初期担当者リスト
        initial_assignees = ['渡邉 祥太', 'hoge', 'fuga']
        save_assignee_list(initial_assignees)
        return initial_assignees

# 担当者リストの保存
def save_assignee_list(assignee_list):
    df_assignees = pd.DataFrame({'担当者名': assignee_list})
    df_assignees.to_csv(ASSIGNEE_FILE, index=False)

# 担当者リストの管理
def manage_assignee_list():
    st.subheader('👥 担当者リスト管理')
    
    # 現在の担当者リストを読み込み
    current_assignees = load_assignee_list()
    
    # 新しい担当者の追加
    col1, col2 = st.columns([3, 1])
    with col1:
        new_assignee = st.text_input('新しい担当者を追加', placeholder='担当者名を入力')
    with col2:
        if st.button('追加', type='secondary'):
            if new_assignee and new_assignee not in current_assignees:
                current_assignees.append(new_assignee)
                save_assignee_list(current_assignees)
                st.success(f'担当者「{new_assignee}」を追加しました！')
                st.rerun()
            elif new_assignee in current_assignees:
                st.warning('既に存在する担当者です')
            else:
                st.warning('担当者名を入力してください')
    
    # 現在の担当者リスト表示と削除
    st.write('**現在の担当者リスト：**')
    for i, assignee in enumerate(current_assignees):
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f'• {assignee}')
        with col2:
            if st.button(f'削除', key=f'delete_{i}', type='secondary'):
                if len(current_assignees) > 1:  # 最低1人は残す
                    current_assignees.pop(i)
                    save_assignee_list(current_assignees)
                    st.success(f'担当者「{assignee}」を削除しました！')
                    st.rerun()
                else:
                    st.warning('担当者は最低1人必要です')

def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        #初期データ
        initial_data = {
            'タスク名': ['Sample'],
            '期限': ['2025-08-11'],
            '担当者': ['渡邉祥太'],
            'ステータス': ['完了'],
            '完了日': ['2025-08-11'],
            '備考': [None]
        }
        return pd.DataFrame(initial_data)

# データの保存
def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# 初期化
if "ai_df" not in st.session_state:
    st.session_state.ai_df = None
if "ai_ready" not in st.session_state:
    st.session_state.ai_ready = False
if "df" not in st.session_state:
    st.session_state.df = load_data()

# 既存のdf変数も更新
df = st.session_state.df

# タイトルの表示
st.title('ToDo管理')

# 担当者リスト管理セクション
with st.expander("👥 担当者リスト管理"):
    manage_assignee_list()

# header2の表示__タスクの登録
## タスクの登録
st.subheader('✅️タスクの登録')

# 複数タスク同時登録
with st.expander("📝 タスク個別登録（推奨）"):
    st.write("**複数のタスクを同時に登録できます**")
    
    # 現在の担当者リストを取得
    current_assignees = load_assignee_list()
    
    # 登録するタスク数を選択
    num_tasks = st.selectbox("登録するタスク数", [3, 5], index=0)
    
    # 複数タスクの入力フォーム
    tasks_to_add = []
    st.write("**タスクを登録してください**")
    for i in range(num_tasks):
        ##st.write(f"**タスク {i+1}**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            task_name = st.text_input(f'タスク名 {i+1}', key=f'name_{i}')
        with col2:
            task_deadline = st.date_input(f'期限 {i+1}', 'today', key=f'deadline_{i}')
        with col3:
            task_assignee = st.selectbox(f'担当者 {i+1}', current_assignees, key=f'assignee_{i}')
        
        # タスクが入力されている場合のみ追加対象に
        if task_name:
            tasks_to_add.append({
                'タスク名': task_name,
                '期限': task_deadline,
                '担当者': task_assignee,
                'ステータス': '未着手',
                '完了日': None,
                '備考': None
            })
    
    # 一括登録ボタン
    if st.button('📋 選択したタスクを一括登録', type='primary'):
        if tasks_to_add:
            # 新しいタスクを既存のDataFrameに追加
            df_new = pd.DataFrame(tasks_to_add)
            df = pd.concat([df, df_new], ignore_index=True)
            
            # データを保存
            save_data(df)
            
            st.success(f'{len(tasks_to_add)}件のタスクを一括登録しました！')
            st.balloons()  # 成功時の演出
            time.sleep(2)
            # ページをリロード
            st.rerun()
        else:
            st.warning('登録するタスクがありません。タスク名を入力してください。')

## タスクの一括登録
with st.expander("📁 一括登録（CSV）"):
    # ファイルアップロードウィジェットの作成
    uploaded_file = st.file_uploader("CSVファイルをアップロードしてください", type=["csv"])

     # ファイルがアップロードされた場合の処理
    if uploaded_file is not None:
        # CSVファイルをデータフレームとして読み込む
        df_csv = pd.read_csv(uploaded_file)
        st.write("アップロードされたファイルの内容:")
        st.dataframe(df_csv)
    
    # タスクの一括登録ボタンを押した場合の処理
        if st.button('タスクの一括登録'):
            try:
                # CSVの各カラムをdataのカラムに割り当ててnew_taskを作成
                new_tasks = []
                for index, row in df_csv.iterrows():
                    new_task = {
                        'タスク名': row.get('タスク名', ''),
                        '期限': row.get('期限', ''),
                        '担当者': row.get('担当者', ''),
                        'ステータス': row.get('ステータス', '未着手'),
                        '完了日': row.get('完了日', None),
                        '備考': row.get('備考', None)
                    }
                    new_tasks.append(new_task)
            
                # 新しいタスクを既存のdataframeに追加
                df_new = pd.DataFrame(new_tasks)
                df = pd.concat([df, df_new], ignore_index=True)
            
                # データを保存
                save_data(df)
            
                st.success(f'{len(new_tasks)}件のタスクを一括登録しました！')
            
            except Exception as e:
                st.error(f'エラーが発生しました: {str(e)}')

## AIがタスクを作る
with st.expander("🧠 AIにタスクを作ってもらう（gpt-4o）"):
    st.write("**やりたいことを伝えると、AIが必要なタスクを考えてくれます**")
    input_text = st.text_input('やりたいことを入力してください：')
    input_date = st.date_input('期日を設定してください')

    # 1) 生成ボタン：押されたときに session_state に結果を格納
    if input_text and st.button('AIに問い合わせる', key='ask_ai'):
        try:
            # AIにタスク生成を依頼
            # タスク名,期限,推定時間,担当者,ステータス,完了日,備考
            prompt = f"""
            以下のやりたいことを実現するために必要なタスクを、以下の形式で具体的に生成してください。
            また、各タスクの期限については、やりたいことの期限から逆算してください。

            やりたいこと：{input_text}
            期限：{input_date}

            出力形式：
            タスク名,期限,詳細,推定工数
            例：
            プロジェクト計画の策定,2025-08-01,プロジェクトの計画をnotionにまとめる,4時間
            チームメンバーとの打ち合わせ,2025-08-01,チームメンバーとkickoffをする,1.5時間
            """

            response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
            # AIの応答を取得
            ai_response = response.choices[0].message.content
            # CSV形式の文字列をDataFrameに変換
            lines = ai_response.strip().split('\n')
            if len(lines) > 1:
                #　ヘッダー行を除いてデータ行のみ取得
                data_lines = [line.strip() for line in lines[1:] if line.strip() and ',' in line]
                
                if data_lines:
                    # CSV文字列を作成
                    csv_string = "タスク名,期限,詳細,推定工数\n" + "\n".join(data_lines)
                    # StringIOを使用してDataFrameに変換 
                    df_ai = pd.read_csv(io.StringIO(csv_string))

                    st.session_state.ai_df = df_ai
                    st.session_state.ai_ready = True
                else:
                    st.error("AIの応答を適切な形式で解析できませんでした。")
            else:
                st.error("AIの応答が空です。")
        except Exception as e:
            st.error(f"エラーが発生しました: {str(e)}")
    
    # 2) 生成結果の表示（ボタンの if の外！）
    if st.session_state.ai_ready and st.session_state.ai_df is not None:
        df_ai = st.session_state.ai_df
        st.write("**AIが生成したタスク一覧：**")
        st.dataframe(df_ai, use_container_width=True)

        # 3) リストに追加ボタン：ここは常に描画されるので正常に反応する
        if st.button('タスクをリストに追加', key='add_ai_tasks'):
            try:
                df_ai_converted = df_ai.copy()
                df_ai_converted['担当者'] = '渡邉 祥太'
                df_ai_converted['ステータス'] = '未着手'
                df_ai_converted['完了日'] = None
                df_ai_converted['備考'] = df_ai_converted['詳細']
                df_ai_converted = df_ai_converted[['タスク名','期限','担当者','ステータス','完了日','備考']]

                st.write("**AIが加工したタスク一覧：**")
                st.dataframe(df_ai_converted, use_container_width=True)

                # 既存 df に追加して保存
                st.session_state.df = pd.concat([st.session_state.df, df_ai_converted], ignore_index=True)
                save_data(st.session_state.df)
                df = st.session_state.df

                st.success(f"{len(df_ai_converted)}件のタスクを追加しました！")
                # 後片付け：一旦生成結果をクリア（必要なら残す）
                st.session_state.ai_ready = False
                st.session_state.ai_df = None
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")

# 現在のタスク一覧を表示
st.subheader('📖 未完了のタスク一覧')
st.write('ChatGPTに繋げる入力欄用意して、この画面からステータスを更新かけるようにしたい')
st.write('例）1と5を完了にして、2と4は期日を1日後ろ倒して')

# 未完了タスクのフィルタリング
filtered_df = df[df['ステータス'] != '完了'].copy()

if not filtered_df.empty:
    st.dataframe(filtered_df)
else:
    st.info("未完了のタスクはありません")

# 完了済みタスクの表示
st.subheader('📈完了済みタスク一覧')
st.write('これまでのタスク消化数を日時でプロットしてみたい')

# 1週間前の日付を計算。日付入力フィールドが2列で横並びに表示
col1, col2 = st.columns(2)
with col1:
    filter_start_date = st.date_input('開始日：', value=datetime.now().date() - timedelta(days=7))
with col2:
    filter_end_date = st.date_input('終了日：', value=datetime.now().date())

# 完了済みタスクを日付範囲でフィルタリング
completed_df = df[df['ステータス'] == '完了'].copy()
if not completed_df.empty:
    # 完了日をdatetime型に変換
    completed_df['完了日'] = pd.to_datetime(completed_df['完了日'])
    # 日付範囲でフィルタリング
    completed_in_days = (completed_df['完了日'].dt.date >= filter_start_date) & (completed_df['完了日'].dt.date <= filter_end_date)
    completed_df = completed_df[completed_in_days]

# フィルタリング後のデータを表示（0件の場合も含む）
if not completed_df.empty:
    # 表示用に完了日をdate型に戻す
    display_df = completed_df.copy()
    display_df['完了日'] = display_df['完了日'].dt.date
    
    st.dataframe(display_df)
    
    # 完了日でグループ化して件数をカウント
    completed_counts = completed_df['完了日'].value_counts()
    
    # 指定期間の全日付を生成
    date_range = pd.date_range(start=filter_start_date, end=filter_end_date, freq='D')
    
    # 各日付の完了タスク数を取得（ない場合は0）
    daily_counts = []
    for date in date_range:
        date_str = date.strftime('%Y-%m-%d')
        count = completed_counts.get(date_str, 0)
        daily_counts.append(count)
    
    # グラフの作成
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # 棒グラフの作成（指定期間の全日付）
    ax.bar(range(len(date_range)), daily_counts)
    
    # 軸ラベルとタイトルの設定
    ax.set_xlabel('Date')
    ax.set_ylabel('Completed Tasks')
    ax.set_title('Daily Task Completion Count')
    
    # x軸の日付ラベルを設定（指定期間の全日付）
    ax.set_xticks(range(len(date_range)))
    ax.set_xticklabels([d.strftime('%Y-%m-%d') for d in date_range], rotation=45)
    
    # Y軸の目盛りを整数刻みに設定
    max_count = max(daily_counts) if daily_counts else 1
    y_min = 0  # 最小値は常に0
    y_max = max(10, max_count + 1)  # デフォルトで10、最大値が10を超える場合はその値+1
    ax.set_yticks(range(0, y_max + 1))
    ax.set_ylim(0, y_max)  # Y軸の範囲を設定
    
    # グラフの表示
    st.pyplot(fig)

else:
    st.info(f"{filter_start_date}から{filter_end_date}の期間内に完了済みのタスクはありません")

