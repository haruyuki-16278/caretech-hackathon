/* 高齢者向け 音声チャットページの動作
 * - ボタンを押して録音開始/終了
 * - 録音した音声をサーバー(/api/voice-chat)に送信
 * - サーバーから受け取った応答(テキスト・音声)を表示・再生する
 * - 音声合成(TTS)がサーバー側で利用できない場合は、
 *   ブラウザ標準の音声合成(Web Speech API)で読み上げる
 */
(() => {
  "use strict";

  const recordButton = document.getElementById("record-button");
  const statusEl = document.getElementById("status");
  const transcriptEl = document.getElementById("transcript-text");
  const replyEl = document.getElementById("reply-text");
  const consultBlock = document.getElementById("consult-info");
  const consultOfficeEl = document.getElementById("consult-office");
  const consultPhoneEl = document.getElementById("consult-phone");
  const consultAddressEl = document.getElementById("consult-address");
  const audioPlayer = document.getElementById("reply-audio");
  const areaInput = document.getElementById("area-input");
  const textForm = document.getElementById("text-fallback-form");
  const textInput = document.getElementById("text-input");

  const STATE_IDLE = "idle";
  const STATE_RECORDING = "recording";
  const STATE_PROCESSING = "processing";

  let state = STATE_IDLE;
  let mediaRecorder = null;
  let recordedChunks = [];

  function setStatus(message) {
    statusEl.textContent = message;
  }

  function setState(next) {
    state = next;
    switch (state) {
      case STATE_IDLE:
        recordButton.disabled = false;
        recordButton.setAttribute("aria-pressed", "false");
        recordButton.textContent = "🎙️ 話しかける";
        break;
      case STATE_RECORDING:
        recordButton.disabled = false;
        recordButton.setAttribute("aria-pressed", "true");
        recordButton.textContent = "⏹️ 話し終わったら押してください";
        break;
      case STATE_PROCESSING:
        recordButton.disabled = true;
        recordButton.setAttribute("aria-pressed", "false");
        recordButton.textContent = "…お返事を考えています";
        break;
    }
  }

  function isVoiceSupported() {
    return Boolean(
      navigator.mediaDevices &&
        navigator.mediaDevices.getUserMedia &&
        window.MediaRecorder
    );
  }

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      recordedChunks = [];
      mediaRecorder = new MediaRecorder(stream);
      mediaRecorder.addEventListener("dataavailable", (event) => {
        if (event.data && event.data.size > 0) {
          recordedChunks.push(event.data);
        }
      });
      mediaRecorder.addEventListener("stop", () => {
        stream.getTracks().forEach((track) => track.stop());
        void handleRecordingStopped();
      });
      mediaRecorder.start();
      setState(STATE_RECORDING);
      setStatus("録音中です。お話しください。終わったらもう一度ボタンを押してください。");
    } catch (error) {
      console.error(error);
      setStatus("マイクを使用できませんでした。ブラウザの設定をご確認ください。");
    }
  }

  function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
    }
  }

  async function handleRecordingStopped() {
    setState(STATE_PROCESSING);
    setStatus("送信しています。しばらくお待ちください…");

    const blob = new Blob(recordedChunks, {
      type: mediaRecorder.mimeType || "audio/webm",
    });

    try {
      await sendAudio(blob);
    } catch (error) {
      console.error(error);
      setStatus("送信中にエラーが発生しました。もう一度お試しください。");
    } finally {
      setState(STATE_IDLE);
    }
  }

  async function sendAudio(blob) {
    const formData = new FormData();
    const extension = blob.type.includes("ogg") ? "ogg" : "webm";
    formData.append("audio", blob, `recording.${extension}`);
    formData.append("session_id", getSessionId());
    if (areaInput && areaInput.value.trim()) {
      formData.append("area", areaInput.value.trim());
    }

    const response = await fetch("/api/voice-chat", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`サーバーエラー: ${response.status}`);
    }

    const data = await response.json();
    renderResult(data);
  }

  async function sendText(text) {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: getSessionId(),
        text,
        area: areaInput && areaInput.value.trim() ? areaInput.value.trim() : null,
      }),
    });

    if (!response.ok) {
      throw new Error(`サーバーエラー: ${response.status}`);
    }

    const data = await response.json();
    renderResult({ ...data, transcript: text, audio_base64: null });
  }

  function renderResult(data) {
    transcriptEl.textContent = data.transcript || "(聞き取れませんでした)";
    replyEl.textContent = data.reply || "";

    if (data.category === "consult" && data.consult_info) {
      consultBlock.hidden = false;
      consultOfficeEl.textContent = data.consult_info.office || "";
      consultPhoneEl.textContent = data.consult_info.phone || "電話番号は窓口にご確認ください";
      consultAddressEl.textContent = data.consult_info.address || "";
    } else {
      consultBlock.hidden = true;
    }

    playReply(data);
    setStatus("お返事です。よろしければ続けてお話しください。");
  }

  function playReply(data) {
    if (data.audio_base64 && data.audio_content_type) {
      const src = `data:${data.audio_content_type};base64,${data.audio_base64}`;
      audioPlayer.src = src;
      audioPlayer.hidden = false;
      audioPlayer.play().catch((error) => {
        console.warn("自動再生に失敗しました。再生ボタンを押してください。", error);
      });
      return;
    }

    audioPlayer.hidden = true;
    speakWithBrowserFallback(data.reply);
  }

  function speakWithBrowserFallback(text) {
    if (!text || !window.speechSynthesis) {
      return;
    }
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "ja-JP";
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  }

  function getSessionId() {
    const key = "voice-chat-session-id";
    let sessionId = window.sessionStorage.getItem(key);
    if (!sessionId) {
      sessionId = `session-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      window.sessionStorage.setItem(key, sessionId);
    }
    return sessionId;
  }

  recordButton.addEventListener("click", () => {
    if (state === STATE_IDLE) {
      void startRecording();
    } else if (state === STATE_RECORDING) {
      stopRecording();
    }
  });

  if (textForm) {
    textForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const text = textInput.value.trim();
      if (!text) {
        return;
      }
      setStatus("送信しています。しばらくお待ちください…");
      sendText(text)
        .catch((error) => {
          console.error(error);
          setStatus("送信中にエラーが発生しました。もう一度お試しください。");
        });
      textInput.value = "";
    });
  }

  if (!isVoiceSupported()) {
    recordButton.disabled = true;
    recordButton.textContent = "この端末では音声入力が使えません";
    setStatus("お使いのブラウザは音声入力に対応していません。下のテキスト欄をご利用ください。");
  } else {
    setState(STATE_IDLE);
    setStatus("ボタンを押して、お話しください。");
  }
})();
