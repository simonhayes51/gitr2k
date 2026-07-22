(() => {
  const views = {
    login: document.getElementById("view-login"),
    lobby: document.getElementById("view-lobby"),
    arena: document.getElementById("view-arena"),
    fight: document.getElementById("view-fight"),
  };

  function show(name) {
    for (const key in views) views[key].hidden = key !== name;
  }

  const state = {
    username: null,
    ws: null,
    currentArena: null,
    moves: [],
    fight: null,
    isSpectator: false,
  };

  const el = {
    usernameInput: document.getElementById("username-input"),
    loginBtn: document.getElementById("login-btn"),
    loginError: document.getElementById("login-error"),
    whoami: document.getElementById("whoami"),
    newsBox: document.getElementById("news-box"),
    arenaList: document.getElementById("arena-list"),
    arenaName: document.getElementById("arena-name"),
    chatLog: document.getElementById("chat-log"),
    chatForm: document.getElementById("chat-form"),
    chatInput: document.getElementById("chat-input"),
    userList: document.getElementById("user-list"),
    fightsList: document.getElementById("fights-list"),
    backToLobby: document.getElementById("back-to-lobby"),
    matchTypeSelect: document.getElementById("match-type-select"),
    fightTitle: document.getElementById("fight-title"),
    commentaryLog: document.getElementById("commentary-log"),
    movesGrid: document.getElementById("moves-grid"),
    leaveFightBtn: document.getElementById("leave-fight-btn"),
    challengeModal: document.getElementById("challenge-modal"),
    challengeText: document.getElementById("challenge-text"),
    challengeAccept: document.getElementById("challenge-accept"),
    challengeDecline: document.getElementById("challenge-decline"),
    toast: document.getElementById("toast"),
  };

  let toastTimer = null;
  function toast(message) {
    el.toast.textContent = message;
    el.toast.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.toast.hidden = true; }, 3000);
  }

  function send(payload) {
    if (state.ws && state.ws.readyState === WebSocket.OPEN) {
      state.ws.send(JSON.stringify(payload));
    }
  }

  function connect(username) {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/ws`);
    state.ws = ws;
    ws.onopen = () => send({ type: "login", username });
    ws.onclose = () => toast("disconnected from server");
    ws.onmessage = (evt) => handleMessage(JSON.parse(evt.data));
  }

  function handleMessage(msg) {
    switch (msg.type) {
      case "welcome":
        state.username = msg.username;
        el.whoami.textContent = `playing as ${msg.username}`;
        el.newsBox.innerHTML = msg.news.map(n => `<p>${escapeHtml(n)}</p>`).join("");
        renderArenaList(msg.arenas);
        show("lobby");
        break;
      case "error":
        toast(msg.message);
        if (!state.username) el.loginError.textContent = msg.message;
        break;
      case "arenas_update":
        renderArenaList(msg.arenas);
        break;
      case "arena_state":
        state.currentArena = msg.name;
        el.arenaName.textContent = msg.name;
        el.chatLog.innerHTML = "";
        msg.history.forEach(addChatLine);
        renderUserList(msg.users);
        send({ type: "list_fights" });
        show("arena");
        break;
      case "user_enter":
        addSystemLine(`${msg.username} entered the arena`);
        if (!el.userList.querySelector(`[data-user="${cssEscape(msg.username)}"]`)) {
          const users = [...el.userList.querySelectorAll("[data-user]")].map(li => li.dataset.user);
          users.push(msg.username);
          renderUserList(users);
        }
        break;
      case "user_leave":
        addSystemLine(`${msg.username} left the arena`);
        el.userList.querySelectorAll(`[data-user="${cssEscape(msg.username)}"]`).forEach(li => li.remove());
        break;
      case "chat":
        addChatLine(msg);
        break;
      case "challenge_received":
        el.challengeText.textContent = `${msg.from} has challenged you to a ${msg.matchType} match!`;
        el.challengeModal.dataset.id = msg.id;
        el.challengeModal.hidden = false;
        break;
      case "challenge_sent":
        toast(`challenge sent to ${msg.to}`);
        break;
      case "challenge_declined":
        toast(`${msg.by} declined your challenge`);
        break;
      case "fight_start":
        state.moves = msg.moves || state.moves;
        state.isSpectator = !!msg.asSpectator;
        renderFight(msg.fight);
        show("fight");
        break;
      case "fight_update":
        renderFight(msg.fight);
        break;
      case "fights_list":
        renderFightsList(msg.fights);
        break;
    }
  }

  function escapeHtml(s) {
    return s.replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }
  function cssEscape(s) { return s.replace(/"/g, '\\"'); }

  function addChatLine({ user, text }) {
    const div = document.createElement("div");
    div.className = "line";
    div.innerHTML = `<span class="user">${escapeHtml(user)}:</span> ${escapeHtml(text)}`;
    el.chatLog.appendChild(div);
    el.chatLog.scrollTop = el.chatLog.scrollHeight;
  }
  function addSystemLine(text) {
    const div = document.createElement("div");
    div.className = "line system";
    div.textContent = text;
    el.chatLog.appendChild(div);
    el.chatLog.scrollTop = el.chatLog.scrollHeight;
  }

  function renderArenaList(arenas) {
    el.arenaList.innerHTML = "";
    arenas.forEach(a => {
      const li = document.createElement("li");
      li.innerHTML = `<span class="name">${escapeHtml(a.name)}</span><span class="count">${a.count} here</span>`;
      const btn = document.createElement("button");
      btn.textContent = "Join";
      btn.onclick = () => send({ type: "join_arena", name: a.name });
      li.appendChild(btn);
      el.arenaList.appendChild(li);
    });
  }

  function renderUserList(usernames) {
    el.userList.innerHTML = "";
    usernames.forEach(u => {
      const li = document.createElement("li");
      li.dataset.user = u;
      li.innerHTML = `<span class="name">${escapeHtml(u)}</span>`;
      if (u !== state.username) {
        const btn = document.createElement("button");
        btn.textContent = "Challenge";
        btn.onclick = () => send({ type: "challenge", target: u, matchType: el.matchTypeSelect.value });
        li.appendChild(btn);
      } else {
        li.innerHTML += `<span class="count">(you)</span>`;
      }
      el.userList.appendChild(li);
    });
  }

  function renderFightsList(fightList) {
    el.fightsList.innerHTML = "";
    if (fightList.length === 0) {
      el.fightsList.innerHTML = "<li><span class=\"count\">no matches in progress</span></li>";
      return;
    }
    fightList.forEach(f => {
      const li = document.createElement("li");
      li.innerHTML = `<span class="name">${escapeHtml(f.participants.join(" vs "))}</span>`;
      const btn = document.createElement("button");
      btn.textContent = "Watch";
      btn.onclick = () => send({ type: "spectate", fightId: f.id });
      li.appendChild(btn);
      el.fightsList.appendChild(li);
    });
  }

  function renderFight(fight) {
    state.fight = fight;
    el.fightTitle.textContent = fight.status === "finished"
      ? `${fight.winner} wins!`
      : `${fight.fighters.map(f => f.username).join(" vs ")} - ${fight.matchType}`;

    fight.fighters.forEach((f, i) => {
      const box = document.getElementById(`fighter-${i}`);
      box.querySelector(".fname").textContent = f.username;
      box.querySelector(".bar.energy .fill").style.width = `${f.energy}%`;
      box.querySelector(".bar.points .fill").style.width = `${Math.min(100, f.points)}%`;
    });

    el.commentaryLog.innerHTML = fight.commentary.map(c => `<p>${escapeHtml(c)}</p>`).join("");
    el.commentaryLog.scrollTop = el.commentaryLog.scrollHeight;

    const me = fight.fighters.find(f => f.username === state.username);
    const iAmFighter = !!me && !state.isSpectator;

    el.movesGrid.innerHTML = "";
    if (iAmFighter && fight.status === "active") {
      state.moves.forEach(m => {
        const btn = document.createElement("button");
        btn.textContent = `${m.name} (${m.energyCost})`;
        btn.disabled = me.energy < m.energyCost;
        btn.onclick = () => send({ type: "fight_action", moveId: m.id });
        el.movesGrid.appendChild(btn);
      });
    }

    el.leaveFightBtn.textContent = fight.status === "finished"
      ? "Back to arena"
      : (state.isSpectator ? "Stop watching" : "Forfeit match");
  }

  el.loginBtn.onclick = () => {
    const name = el.usernameInput.value.trim();
    if (!name) return;
    el.loginError.textContent = "";
    connect(name);
  };
  el.usernameInput.addEventListener("keydown", (e) => { if (e.key === "Enter") el.loginBtn.click(); });

  el.chatForm.onsubmit = (e) => {
    e.preventDefault();
    const text = el.chatInput.value.trim();
    if (!text) return;
    send({ type: "chat", text });
    el.chatInput.value = "";
  };

  el.backToLobby.onclick = () => {
    send({ type: "list_fights" });
    show("lobby");
  };

  el.challengeAccept.onclick = () => {
    send({ type: "respond_challenge", id: el.challengeModal.dataset.id, accept: true });
    el.challengeModal.hidden = true;
  };
  el.challengeDecline.onclick = () => {
    send({ type: "respond_challenge", id: el.challengeModal.dataset.id, accept: false });
    el.challengeModal.hidden = true;
  };

  el.leaveFightBtn.onclick = () => {
    if (state.isSpectator) {
      send({ type: "stop_spectate" });
    } else {
      send({ type: "leave_fight" });
    }
    state.isSpectator = false;
    show("arena");
  };
})();
