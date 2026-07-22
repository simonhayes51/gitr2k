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
    arenaUsers: [],
    moves: [],
    fight: null,
    isSpectator: false,
    ignoreList: new Set(),
    standardPhrases: [],
    dm: { threads: {}, active: null },
  };

  const el = {
    usernameInput: document.getElementById("username-input"),
    passwordInput: document.getElementById("password-input"),
    loginBtn: document.getElementById("login-btn"),
    loginError: document.getElementById("login-error"),
    whoami: document.getElementById("whoami"),
    newsBox: document.getElementById("news-box"),
    recordBox: document.getElementById("record-box"),
    arenaTree: document.getElementById("arena-tree"),
    arenaName: document.getElementById("arena-name"),
    chatLog: document.getElementById("chat-log"),
    chatForm: document.getElementById("chat-form"),
    chatInput: document.getElementById("chat-input"),
    phraseRow: document.getElementById("phrase-row"),
    editPhrasesBtn: document.getElementById("edit-phrases-btn"),
    userList: document.getElementById("user-list"),
    fightsList: document.getElementById("fights-list"),
    backToLobby: document.getElementById("back-to-lobby"),
    matchTypeSelect: document.getElementById("match-type-select"),
    fightTitle: document.getElementById("fight-title"),
    teamsContainer: document.getElementById("teams-container"),
    inviteRow: document.getElementById("invite-row"),
    inviteSelect: document.getElementById("invite-select"),
    inviteBtn: document.getElementById("invite-btn"),
    targetRow: document.getElementById("target-row"),
    targetSelect: document.getElementById("target-select"),
    commentaryLog: document.getElementById("commentary-log"),
    movesGrid: document.getElementById("moves-grid"),
    leaveFightBtn: document.getElementById("leave-fight-btn"),
    challengeModal: document.getElementById("challenge-modal"),
    challengeText: document.getElementById("challenge-text"),
    challengeAccept: document.getElementById("challenge-accept"),
    challengeDecline: document.getElementById("challenge-decline"),
    teamInviteModal: document.getElementById("team-invite-modal"),
    teamInviteText: document.getElementById("team-invite-text"),
    teamInviteAccept: document.getElementById("team-invite-accept"),
    teamInviteDecline: document.getElementById("team-invite-decline"),
    phrasesModal: document.getElementById("phrases-modal"),
    phrasesTextarea: document.getElementById("phrases-textarea"),
    phrasesSave: document.getElementById("phrases-save"),
    phrasesCancel: document.getElementById("phrases-cancel"),
    dmPanel: document.getElementById("dm-panel"),
    dmTabs: document.getElementById("dm-tabs"),
    dmClose: document.getElementById("dm-close"),
    dmLog: document.getElementById("dm-log"),
    dmForm: document.getElementById("dm-form"),
    dmInput: document.getElementById("dm-input"),
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

  function connect(username, password) {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/ws`);
    state.ws = ws;
    ws.onopen = () => send({ type: "login", username, password });
    ws.onclose = () => toast("disconnected from server");
    ws.onmessage = (evt) => handleMessage(JSON.parse(evt.data));
  }

  function escapeHtml(s) {
    return s.replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function handleMessage(msg) {
    switch (msg.type) {
      case "welcome":
        state.username = msg.username;
        state.ignoreList = new Set(msg.ignoreList);
        state.standardPhrases = msg.standardPhrases;
        el.whoami.textContent = `playing as ${msg.username}`;
        el.newsBox.innerHTML = msg.news.map(n => `<p>${escapeHtml(n)}</p>`).join("");
        el.recordBox.textContent = `Your record: ${msg.wins} wins - ${msg.losses} losses`;
        renderArenaTree(msg.arenas);
        show("lobby");
        break;
      case "error":
        toast(msg.message);
        if (!state.username) el.loginError.textContent = msg.message;
        break;
      case "arenas_update":
        renderArenaTree(msg.arenas);
        break;
      case "arena_state":
        state.currentArena = msg.name;
        state.arenaUsers = msg.users;
        el.arenaName.textContent = msg.name;
        el.chatLog.innerHTML = "";
        msg.history.forEach(addChatLine);
        renderUserList();
        renderPhraseRow();
        send({ type: "list_fights" });
        show("arena");
        break;
      case "user_enter":
        addSystemLine(`${msg.username} entered the arena`);
        if (!state.arenaUsers.includes(msg.username)) state.arenaUsers.push(msg.username);
        renderUserList();
        break;
      case "user_leave":
        addSystemLine(`${msg.username} left the arena`);
        state.arenaUsers = state.arenaUsers.filter(u => u !== msg.username);
        renderUserList();
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
      case "team_invite":
        el.teamInviteText.textContent = `${msg.from} wants you to join their side (${msg.teammates.join(" & ")}) against ${msg.opponents.join(" & ")}!`;
        el.teamInviteModal.dataset.id = msg.id;
        el.teamInviteModal.hidden = false;
        break;
      case "team_invite_sent":
        toast(`invite sent to ${msg.to}`);
        break;
      case "team_invite_declined":
        toast(`${msg.by} declined joining the match`);
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
      case "private_message_sent":
        recordDm(msg.to, { from: state.username, text: msg.text, ts: msg.ts, mine: true });
        break;
      case "private_message_received":
        recordDm(msg.from, { from: msg.from, text: msg.text, ts: msg.ts, mine: false });
        el.dmPanel.hidden = false;
        toast(`new message from ${msg.from}`);
        break;
      case "ignore_list_updated":
        state.ignoreList = new Set(msg.ignoreList);
        renderUserList();
        break;
      case "phrases_updated":
        state.standardPhrases = msg.standardPhrases;
        renderPhraseRow();
        break;
    }
  }

  // ---- chat / arena ----

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

  function renderArenaTree(countries) {
    el.arenaTree.innerHTML = "";
    countries.forEach(({ country, arenas }) => {
      const details = document.createElement("details");
      details.open = true;
      const summary = document.createElement("summary");
      summary.textContent = country;
      details.appendChild(summary);
      const ul = document.createElement("ul");
      ul.className = "list";
      arenas.forEach(a => {
        const li = document.createElement("li");
        li.innerHTML = `<span class="name">${escapeHtml(a.name)}</span><span class="count">${a.count} here</span>`;
        const btn = document.createElement("button");
        btn.textContent = "Join";
        btn.onclick = () => send({ type: "join_arena", name: a.name });
        li.appendChild(btn);
        ul.appendChild(li);
      });
      details.appendChild(ul);
      el.arenaTree.appendChild(details);
    });
  }

  function renderUserList() {
    el.userList.innerHTML = "";
    state.arenaUsers.forEach(u => {
      const li = document.createElement("li");
      li.dataset.user = u;
      li.innerHTML = `<span class="name">${escapeHtml(u)}</span>`;
      if (u !== state.username) {
        const actions = document.createElement("div");
        actions.className = "actions";

        const challengeBtn = document.createElement("button");
        challengeBtn.className = "small";
        challengeBtn.textContent = "Challenge";
        challengeBtn.onclick = () => send({ type: "challenge", target: u, matchType: el.matchTypeSelect.value });
        actions.appendChild(challengeBtn);

        const msgBtn = document.createElement("button");
        msgBtn.className = "small secondary";
        msgBtn.textContent = "Message";
        msgBtn.onclick = () => openDm(u);
        actions.appendChild(msgBtn);

        const ignoring = state.ignoreList.has(u);
        const ignoreBtn = document.createElement("button");
        ignoreBtn.className = "small secondary" + (ignoring ? " ignoring" : "");
        ignoreBtn.textContent = ignoring ? "Unignore" : "Ignore";
        ignoreBtn.onclick = () => send({ type: "set_ignore", target: u, ignore: !ignoring });
        actions.appendChild(ignoreBtn);

        li.appendChild(actions);
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
      const label = `${f.teamA.join(" & ")} vs ${f.teamB.join(" & ")}`;
      li.innerHTML = `<span class="name">${escapeHtml(label)}</span>`;
      const btn = document.createElement("button");
      btn.textContent = "Watch";
      btn.onclick = () => send({ type: "spectate", fightId: f.id });
      li.appendChild(btn);
      el.fightsList.appendChild(li);
    });
  }

  function renderPhraseRow() {
    el.phraseRow.innerHTML = "";
    state.standardPhrases.forEach(p => {
      const btn = document.createElement("button");
      btn.className = "secondary";
      btn.textContent = p;
      btn.onclick = () => send({ type: "chat", text: p });
      el.phraseRow.appendChild(btn);
    });
  }

  // ---- fight ----

  function fighterCard(f, isWinner) {
    const div = document.createElement("div");
    div.className = "fighter" + (isWinner ? " winner" : "");
    div.innerHTML = `
      <div class="fname">${escapeHtml(f.username)}</div>
      <div class="bar-label">Energy</div>
      <div class="bar energy"><div class="fill" style="width:${f.energy}%"></div></div>
      <div class="bar-label">Points</div>
      <div class="bar points"><div class="fill" style="width:${Math.min(100, f.points)}%"></div></div>
    `;
    return div;
  }

  function renderFight(fight) {
    state.fight = fight;
    const teamAName = fight.teamA.map(f => f.username).join(" & ");
    const teamBName = fight.teamB.map(f => f.username).join(" & ");

    if (fight.status === "finished") {
      const winners = fight.winnerTeam === "a" ? fight.teamA : fight.teamB;
      el.fightTitle.textContent = `${winners.map(f => f.username).join(" & ")} wins!`;
    } else {
      el.fightTitle.textContent = `${teamAName} vs ${teamBName} - ${fight.matchType}`;
    }

    el.teamsContainer.innerHTML = "";
    const colA = document.createElement("div");
    colA.className = "team-col";
    fight.teamA.forEach(f => colA.appendChild(fighterCard(f, fight.status === "finished" && fight.winnerTeam === "a")));
    const vs = document.createElement("div");
    vs.className = "vs";
    vs.textContent = "VS";
    const colB = document.createElement("div");
    colB.className = "team-col";
    fight.teamB.forEach(f => colB.appendChild(fighterCard(f, fight.status === "finished" && fight.winnerTeam === "b")));
    el.teamsContainer.appendChild(colA);
    el.teamsContainer.appendChild(vs);
    el.teamsContainer.appendChild(colB);

    el.commentaryLog.innerHTML = fight.commentary.map(c => `<p>${escapeHtml(c)}</p>`).join("");
    el.commentaryLog.scrollTop = el.commentaryLog.scrollHeight;

    const mySide = fight.teamA.some(f => f.username === state.username) ? "a" : (fight.teamB.some(f => f.username === state.username) ? "b" : null);
    const me = mySide === "a" ? fight.teamA.find(f => f.username === state.username) : (mySide === "b" ? fight.teamB.find(f => f.username === state.username) : null);
    const iAmFighter = !!me && !state.isSpectator;
    const opponents = mySide === "a" ? fight.teamB : (mySide === "b" ? fight.teamA : []);
    const myTeam = mySide === "a" ? fight.teamA : (mySide === "b" ? fight.teamB : []);

    el.movesGrid.innerHTML = "";
    if (iAmFighter && fight.status === "active") {
      state.moves.forEach(m => {
        const btn = document.createElement("button");
        btn.textContent = `${m.name} (${m.energyCost})`;
        btn.disabled = me.energy < m.energyCost;
        btn.onclick = () => send({ type: "fight_action", moveId: m.id, target: el.targetSelect.value || undefined });
        el.movesGrid.appendChild(btn);
      });
    }

    el.targetRow.hidden = !(iAmFighter && fight.status === "active" && opponents.length > 1);
    if (!el.targetRow.hidden) {
      el.targetSelect.innerHTML = opponents.map(o => `<option value="${escapeHtml(o.username)}">${escapeHtml(o.username)}</option>`).join("");
    }

    el.inviteRow.hidden = !(iAmFighter && fight.status === "active" && myTeam.length < 2);
    if (!el.inviteRow.hidden) {
      const fightUsers = new Set([...fight.teamA, ...fight.teamB].map(f => f.username));
      const candidates = state.arenaUsers.filter(u => u !== state.username && !fightUsers.has(u));
      el.inviteSelect.innerHTML = candidates.length
        ? candidates.map(u => `<option value="${escapeHtml(u)}">${escapeHtml(u)}</option>`).join("")
        : `<option value="">(nobody available in this arena)</option>`;
    }

    el.leaveFightBtn.textContent = fight.status === "finished"
      ? "Back to arena"
      : (state.isSpectator ? "Stop watching" : "Forfeit match");
  }

  // ---- private messages ----

  function recordDm(withUser, entry) {
    if (!state.dm.threads[withUser]) state.dm.threads[withUser] = [];
    state.dm.threads[withUser].push(entry);
    if (!state.dm.active) state.dm.active = withUser;
    renderDm();
  }

  function openDm(withUser) {
    if (!state.dm.threads[withUser]) state.dm.threads[withUser] = [];
    state.dm.active = withUser;
    el.dmPanel.hidden = false;
    renderDm();
  }

  function renderDm() {
    el.dmTabs.innerHTML = "";
    Object.keys(state.dm.threads).forEach(u => {
      const btn = document.createElement("button");
      btn.textContent = u;
      btn.className = u === state.dm.active ? "active" : "";
      btn.onclick = () => { state.dm.active = u; renderDm(); };
      el.dmTabs.appendChild(btn);
    });

    el.dmLog.innerHTML = "";
    const thread = state.dm.threads[state.dm.active] || [];
    thread.forEach(m => {
      const div = document.createElement("div");
      div.className = "line";
      div.innerHTML = `<span class="user">${escapeHtml(m.mine ? "you" : m.from)}:</span> ${escapeHtml(m.text)}`;
      el.dmLog.appendChild(div);
    });
    el.dmLog.scrollTop = el.dmLog.scrollHeight;
  }

  // ---- wiring ----

  el.loginBtn.onclick = () => {
    const name = el.usernameInput.value.trim();
    const password = el.passwordInput.value;
    if (!name || !password) return;
    el.loginError.textContent = "";
    connect(name, password);
  };
  el.passwordInput.addEventListener("keydown", (e) => { if (e.key === "Enter") el.loginBtn.click(); });

  el.chatForm.onsubmit = (e) => {
    e.preventDefault();
    const text = el.chatInput.value.trim();
    if (!text) return;
    send({ type: "chat", text });
    el.chatInput.value = "";
  };

  el.backToLobby.onclick = () => {
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

  el.teamInviteAccept.onclick = () => {
    send({ type: "respond_team_invite", id: el.teamInviteModal.dataset.id, accept: true });
    el.teamInviteModal.hidden = true;
  };
  el.teamInviteDecline.onclick = () => {
    send({ type: "respond_team_invite", id: el.teamInviteModal.dataset.id, accept: false });
    el.teamInviteModal.hidden = true;
  };

  el.inviteBtn.onclick = () => {
    const target = el.inviteSelect.value;
    if (target) send({ type: "invite_partner", username: target });
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

  el.editPhrasesBtn.onclick = () => {
    el.phrasesTextarea.value = state.standardPhrases.join("\n");
    el.phrasesModal.hidden = false;
  };
  el.phrasesCancel.onclick = () => { el.phrasesModal.hidden = true; };
  el.phrasesSave.onclick = () => {
    const phrases = el.phrasesTextarea.value.split("\n").map(s => s.trim()).filter(Boolean);
    send({ type: "save_phrases", phrases });
    el.phrasesModal.hidden = true;
  };

  el.dmClose.onclick = () => { el.dmPanel.hidden = true; };
  el.dmForm.onsubmit = (e) => {
    e.preventDefault();
    const text = el.dmInput.value.trim();
    if (!text || !state.dm.active) return;
    send({ type: "private_message", to: state.dm.active, text });
    el.dmInput.value = "";
  };
})();
