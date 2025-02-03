import streamlit as st
import random
import math
import itertools
import pandas as pd

# 남자와 여자를 위한 별도 색상 리스트 (dummy 플레이어는 색상 적용하지 않음)
MALE_COLORS = ["blue", "green", "red", "orange", "purple"]
FEMALE_COLORS = ["pink", "magenta", "violet", "brown", "gold"]

# =======================
# [Dummy 플레이어 추가 함수]
# =======================
def add_dummy_players(players, mode):
    new_players = players.copy()
    # 단식: 전체 플레이어 수가 홀수이면 dummy 추가
    if mode == "단식":
        if len(new_players) % 2 == 1:
            dummy_id = max(p["id"] for p in new_players) + 1 if new_players else 0
            new_players.append({"id": dummy_id, "name": "Bye", "gender": "Bye", "dummy": True})
    elif mode in ["남복", "여복"]:
        # 해당 성별: if count is odd, add a dummy for that gender
        gender = "남자" if mode == "남복" else "여자"
        gender_players = [p for p in new_players if p["gender"] == gender]
        if len(gender_players) % 2 == 1:
            dummy_id = max(p["id"] for p in new_players) + 1
            new_players.append({"id": dummy_id, "name": "Bye", "gender": gender, "dummy": True})
    elif mode == "혼복":
        # 혼합 모드: 전체 플레이어 수가 홀수 -> add dummy
        if len(new_players) % 2 == 1:
            dummy_id = max(p["id"] for p in new_players) + 1
            new_players.append({"id": dummy_id, "name": "Bye", "gender": "Bye", "dummy": True})
        # 또한, 각 성별의 수가 홀수이면 각각 dummy 추가
        males = [p for p in new_players if p["gender"]=="남자"]
        females = [p for p in new_players if p["gender"]=="여자"]
        if len(males) % 2 == 1:
            dummy_id = max(p["id"] for p in new_players) + 1
            new_players.append({"id": dummy_id, "name": "Bye", "gender": "남자", "dummy": True})
        if len(females) % 2 == 1:
            dummy_id = max(p["id"] for p in new_players) + 1
            new_players.append({"id": dummy_id, "name": "Bye", "gender": "여자", "dummy": True})
    return new_players

# =======================
# [플레이어 출력 포맷 함수]
# =======================
def format_player(p):
    if p.get("dummy", False):
        return "Bye"
    return f"{p['name']} ({p['gender']})"

# =======================
# [매치 생성 관련 함수]
# =======================

# --- 단식 매치 생성 (1:1) ---
def generate_matches_singles(players, total_matches):
    match_count = {p["id"]: 0 for p in players}
    previous_match = set()
    matches = []
    for i in range(total_matches):
        candidates = sorted(players, key=lambda p: (match_count[p["id"]], random.random()))
        chosen = []
        for p in candidates:
            if p["id"] not in previous_match:
                chosen.append(p)
                if len(chosen) == 2:
                    break
        if len(chosen) < 2:
            chosen = candidates[:2]
        matches.append(chosen)
        for p in chosen:
            # dummy 매치는 카운트하지 않음
            if not p.get("dummy", False):
                match_count[p["id"]] += 1
        previous_match = set(p["id"] for p in chosen if not p.get("dummy", False))
    return matches

# --- 복식(남복/여복) 매치 생성 (2:2) ---
def generate_matches_doubles(players, total_matches, gender):
    available_players = [p for p in players if p["gender"] == gender]
    if len(available_players) < 4:
        st.error(f"{gender} 플레이어가 4명 미만입니다. {gender} 복식을 구성할 수 없습니다.")
        return []
    match_count = {p["id"]: 0 for p in available_players}
    previous_match = set()
    team_pair_history = {}
    matches = []
    for i in range(total_matches):
        candidates = sorted(available_players, key=lambda p: (match_count[p["id"]], random.random()))
        selected = []
        for p in candidates:
            if p["id"] not in previous_match:
                selected.append(p)
            if len(selected) == 4:
                break
        if len(selected) < 4:
            selected = candidates[:4]
        possible_pairings = [
            ((selected[0], selected[1]), (selected[2], selected[3])),
            ((selected[0], selected[2]), (selected[1], selected[3])),
            ((selected[0], selected[3]), (selected[1], selected[2]))
        ]
        best_pairing = None
        best_cost = float('inf')
        for pairing in possible_pairings:
            team1 = tuple(sorted([pairing[0][0]["id"], pairing[0][1]["id"]]))
            team2 = tuple(sorted([pairing[1][0]["id"], pairing[1][1]["id"]]))
            cost = team_pair_history.get(team1, 0) + team_pair_history.get(team2, 0)
            if cost < best_cost:
                best_cost = cost
                best_pairing = pairing
        pairing = best_pairing
        matches.append(pairing)
        team1 = tuple(sorted([pairing[0][0]["id"], pairing[0][1]["id"]]))
        team2 = tuple(sorted([pairing[1][0]["id"], pairing[1][1]["id"]]))
        team_pair_history[team1] = team_pair_history.get(team1, 0) + 1
        team_pair_history[team2] = team_pair_history.get(team2, 0) + 1
        for p in selected:
            if not p.get("dummy", False):
                match_count[p["id"]] += 1
        previous_match = set(p["id"] for p in selected if not p.get("dummy", False))
    return matches

# --- 혼복 매치 생성 (혼합 매치와 다수 성별 복식 포함) ---
def generate_matches_mixed(players, total_matches):
    M = sum(1 for p in players if p["gender"]=="남자" and not p.get("dummy", False))
    F = sum(1 for p in players if p["gender"]=="여자" and not p.get("dummy", False))
    # 남녀 수가 동일하면 순수 혼합 매치로 구성
    if M == F:
        return generate_matches_mixed_regular(players, total_matches)
    if M > F:
        X = round((2 * F * total_matches) / (M + F))
        if X > total_matches:
            X = total_matches
        mixed_matches = generate_matches_mixed_regular(players, X)
        same_matches = generate_matches_doubles(players, total_matches - X, gender="남자")
        matches = mixed_matches + same_matches
        random.shuffle(matches)
        return matches
    else:
        X = round((2 * M * total_matches) / (M + F))
        if X > total_matches:
            X = total_matches
        mixed_matches = generate_matches_mixed_regular(players, X)
        same_matches = generate_matches_doubles(players, total_matches - X, gender="여자")
        matches = mixed_matches + same_matches
        random.shuffle(matches)
        return matches

def generate_matches_mixed_regular(players, total_matches):
    match_count = {p["id"]: 0 for p in players}
    previous_match = set()
    team_pair_history = {}
    matches = []
    for i in range(total_matches):
        sorted_players = sorted(players, key=lambda p: (match_count[p["id"]], random.random()))
        best_combo = None
        best_diff = float('inf')
        for combo in itertools.combinations(sorted_players, 4):
            males = sum(1 for p in combo if p["gender"]=="남자")
            females = 4 - males
            diff = abs(males - females)
            if diff < best_diff:
                best_diff = diff
                best_combo = combo
            if best_diff == 0:
                break
        selected = list(best_combo)
        males = [p for p in selected if p["gender"]=="남자"]
        females = [p for p in selected if p["gender"]=="여자"]
        if len(males)==2 and len(females)==2:
            possible_pairings = [
                ((males[0], females[0]), (males[1], females[1])),
                ((males[0], females[1]), (males[1], females[0]))
            ]
            pairing = random.choice(possible_pairings)
        else:
            pairing = ((selected[0], selected[1]), (selected[2], selected[3]))
        matches.append(pairing)
        for p in selected:
            match_count[p["id"]] += 1
        previous_match = set(p["id"] for p in selected)
    return matches

# =======================
# [스케줄 균등도 평가 함수]
# =======================
def compute_match_counts(schedule, game_method, players):
    counts = {p["id"]: 0 for p in players if not p.get("dummy", False)}
    if game_method == "단식":
        for match in schedule:
            for p in match:
                if not p.get("dummy", False):
                    counts[p["id"]] += 1
    else:
        for match in schedule:
            for team in match:
                for p in team:
                    if not p.get("dummy", False):
                        counts[p["id"]] += 1
    return counts

def balance_schedule(gen_func, players, total_matches, game_method, trials=20):
    best_schedule = None
    best_diff = float('inf')
    for i in range(trials):
        schedule = gen_func(players, total_matches)
        counts = compute_match_counts(schedule, game_method, players)
        diff = max(counts.values()) - min(counts.values())
        if diff < best_diff:
            best_diff = diff
            best_schedule = schedule
        if best_diff == 0:
            break
    return best_schedule

# =======================
# [대진표 표 출력 함수]
# =======================
def display_schedule(matches, game_method):
    match_list = []
    for idx, match in enumerate(matches):
        if game_method == "단식":
            p1, p2 = match
            team1 = format_player(p1)
            team2 = format_player(p2)
        else:
            team1_players, team2_players = match
            team1 = " & ".join([format_player(p) for p in team1_players])
            team2 = " & ".join([format_player(p) for p in team2_players])
        match_list.append([f"Match {idx+1}", team1, team2])
    df = pd.DataFrame(match_list, columns=["Match", "Team 1", "Team 2"])
    st.dataframe(df)

# =======================
# [플레이어 매치 횟수 출력 함수]
# =======================
def display_player_stats(matches, players, game_method):
    counts = compute_match_counts(matches, game_method, players)
    stats_list = []
    for p in players:
        if not p.get("dummy", False):
            stats_list.append([p["name"], p["gender"], counts[p["id"]]])
    df_stats = pd.DataFrame(stats_list, columns=["Player", "Gender", "Match Count"])
    st.dataframe(df_stats)

# =======================
# [메인 UI – 설정 & 플레이어 입력]
# =======================
st.title("🎾 테니스 매칭 스케줄 생성기")

st.header("1. 세팅")
num_players_input = st.number_input("인원수 입력", min_value=1, value=8, step=1)
game_count_option = st.selectbox("매칭당 게임수 선택", options=["4게임 (20분)", "6게임 (30분)"])
game_method = st.selectbox("게임 방법 선택", options=["단식", "남복", "여복", "혼복"])
game_time_hours = st.number_input("게임 시간 입력 (시간)", min_value=0.5, value=6.0, step=0.5)
# 테니스 코트 갯수 입력은 제거

if st.button("세팅 확인"):
    st.session_state.settings_confirmed = True
    st.session_state.num_players = int(num_players_input)
    st.session_state.game_count = 4 if "4게임" in game_count_option else 6
    st.session_state.game_method = game_method
    st.session_state.game_time = game_time_hours

if st.session_state.get("settings_confirmed", False):
    st.header("2. 플레이어 정보 입력")
    num_players = st.session_state.num_players
    players = []
    for i in range(num_players):
        col1, col2 = st.columns([2, 1])
        with col1:
            name = st.text_input(f"플레이어 {i+1} 이름", key=f"name_{i}")
        with col2:
            gender = st.selectbox(f"플레이어 {i+1} 성별", options=["남자", "여자"], key=f"gender_{i}")
        if not name:
            name = f"Player{i+1}"
        players.append({"id": i, "name": name, "gender": gender})
    # 플레이어 정보를 dummy 추가를 위해 처리 (홀수인원 또는 각 성별 홀수인 경우)
    players = add_dummy_players(players, st.session_state.game_method)
    st.session_state.players = players
    # 플레이어별 색상 매핑 (dummy 플레이어는 색상 할당하지 않음)
    color_map = {}
    male_index = 0
    female_index = 0
    for p in players:
        if p.get("dummy", False):
            continue
        if p["gender"] == "남자":
            color_map[p["id"]] = MALE_COLORS[male_index % len(MALE_COLORS)]
            male_index += 1
        else:
            color_map[p["id"]] = FEMALE_COLORS[female_index % len(FEMALE_COLORS)]
            female_index += 1
    st.session_state.color_map = color_map

    st.header("3. 대진표 생성")
    match_duration = 20 if st.session_state.game_count == 4 else 30
    total_matches = math.floor(st.session_state.game_time * 60 / match_duration)
    st.write(f"총 매치 수: {total_matches}회")

    if st.button("대진표 만들기"):
        if st.session_state.game_method == "단식":
            schedule = balance_schedule(generate_matches_singles, players, total_matches, "단식", trials=20)
        elif st.session_state.game_method == "남복":
            schedule = balance_schedule(lambda players, tm: generate_matches_doubles(players, tm, gender="남자"),
                                        players, total_matches, "남복", trials=20)
        elif st.session_state.game_method == "여복":
            schedule = balance_schedule(lambda players, tm: generate_matches_doubles(players, tm, gender="여자"),
                                        players, total_matches, "여복", trials=20)
        elif st.session_state.game_method == "혼복":
            schedule = balance_schedule(generate_matches_mixed, players, total_matches, "혼복", trials=20)
        st.session_state.matches = schedule
        st.success("대진표가 생성되었습니다.")
        display_schedule(schedule, st.session_state.game_method)
        st.markdown("### 각 플레이어의 매치 횟수")
        display_player_stats(schedule, st.session_state.players, st.session_state.game_method)

    if st.button("섞기"):
        players = st.session_state.players
        total_matches = math.floor(st.session_state.game_time * 60 / match_duration)
        if st.session_state.game_method == "단식":
            schedule = balance_schedule(generate_matches_singles, players, total_matches, "단식", trials=20)
        elif st.session_state.game_method == "남복":
            schedule = balance_schedule(lambda players, tm: generate_matches_doubles(players, tm, gender="남자"),
                                        players, total_matches, "남복", trials=20)
        elif st.session_state.game_method == "여복":
            schedule = balance_schedule(lambda players, tm: generate_matches_doubles(players, tm, gender="여자"),
                                        players, total_matches, "여복", trials=20)
        elif st.session_state.game_method == "혼복":
            schedule = balance_schedule(generate_matches_mixed, players, total_matches, "혼복", trials=20)
        st.session_state.matches = schedule
        st.success("대진표가 다시 생성되었습니다.")
        display_schedule(schedule, st.session_state.game_method)
        st.markdown("### 각 플레이어의 매치 횟수")
        display_player_stats(schedule, st.session_state.players, st.session_state.game_method)
