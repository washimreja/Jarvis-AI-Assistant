# 🤖 JARVIS (MARK LIII) — কীভাবে চালাবেন

## ✅ Setup সম্পূর্ণ হয়েছে!

আপনার JARVIS assistant এর **দুটি version** তৈরি হয়েছে:

### 1️⃣ **Development Version** (Python script)
📁 Location: `f:\WASHIM-PROJECT\Hey-ira-main\Hey-ira-main\main.py`

### 2️⃣ **Standalone EXE** (Python ছাড়াই চলবে)
📁 Location: `f:\WASHIM-PROJECT\Hey-ira-main\Hey-ira-main\dist\JARVIS\JARVIS.exe`

---

## 🚀 কীভাবে চালাবেন

### পদ্ধতি ১: Python Script দিয়ে (Recommended for development)

1. **PowerShell বা CMD খুলুন**
2. Project folder এ যান:
   ```powershell
   cd "f:\WASHIM-PROJECT\Hey-ira-main\Hey-ira-main"
   ```

3. Virtual environment activate করুন:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
   
   অথবা সরাসরি:
   ```powershell
   .\venv\Scripts\python.exe main.py
   ```

---

### পদ্ধতি ২: Standalone EXE দিয়ে (সবচেয়ে সহজ)

1. **File Explorer** খুলুন
2. এই folder এ যান:
   ```
   f:\WASHIM-PROJECT\Hey-ira-main\Hey-ira-main\dist\JARVIS
   ```

3. **`JARVIS.exe`** ডাবল-ক্লিক করুন

**অথবা** Command line থেকে:
```powershell
cd "f:\WASHIM-PROJECT\Hey-ira-main\Hey-ira-main\dist\JARVIS"
.\JARVIS.exe
```

---

## ⚙️ প্রথমবার চালানোর আগে

### 🔑 Gemini API Key লাগবে (ফ্রি)

1. যান: https://aistudio.google.com/apikey
2. **"Create API Key"** ক্লিক করুন
3. Key টা copy করুন

4. এই file খুলুন:
   ```
   f:\WASHIM-PROJECT\Hey-ira-main\Hey-ira-main\config\api_keys.json
   ```

5. `"YOUR_GEMINI_API_KEY_HERE"` এর জায়গায় আপনার key বসান:
   ```json
   {
     "gemini_api_key": "আপনার_key_এখানে",
     ...
   }
   ```

6. Save করুন (Ctrl+S)

---

## 📦 EXE কোথায় নিয়ে যাবেন

যদি অন্য কম্পিউটারে চালাতে চান:

1. **পুরো `dist\JARVIS` folder টা** copy করুন (শুধু .exe না!)
2. সেই folder এ `JARVIS.exe` double-click করুন

**গুরুত্বপূর্ণ:** 
- ⚠️ শুধু `JARVIS.exe` একা copy করলে চলবে না
- ✅ পুরো `dist\JARVIS` folder টা নিতে হবে (size: ~500-700 MB)

---

## 🎯 Shortcut তৈরি করুন (Optional)

Desktop এ shortcut তৈরির জন্য:

1. File Explorer এ যান:
   ```
   f:\WASHIM-PROJECT\Hey-ira-main\Hey-ira-main\dist\JARVIS
   ```

2. `JARVIS.exe` এ **Right-click** করুন
3. **"Create shortcut"** select করুন
4. Shortcut টা Desktop এ drag করুন

এখন Desktop থেকেই চালাতে পারবেন! 🚀

---

## 🎙️ প্রথম বার চালানোর পর

### UI খুললে:
- ⚙️ **Settings** এ গিয়ে **Audio Devices** select করুন (microphone + speaker)
- 🗣️ **Voice** পছন্দমতো change করতে পারবেন (5টা option: Charon, Puck, Kore, Fenrir, Aoede)
- 🎨 **Theme color** change করতে পারবেন

### Wake Word (Optional):
- ⚙️ **Settings** → **WAKE WORD** → **"Download Model"** click করুন
- তারপর toggle ON করলে "**Hey Jarvis**" বললে wake হবে

---

## 📂 File Structure

```
dist\JARVIS\                        ← এটা portable — পুরোটা copy করুন
├── JARVIS.exe                      ← Main executable
├── Python312.dll                   ← Python runtime
├── actions\                        ← সব voice commands
├── plugins\                        ← Custom plugins
├── config\
│   ├── api_keys.json              ← আপনার Gemini API key
│   └── jarvis.ico                 ← Icon
├── core\
│   └── prompt.txt                 ← AI personality
├── dashboard\
│   └── static\                    ← Remote control web UI
└── _internal\                     ← সব libraries এখানে
```

---

## 🔧 Troubleshooting

### ❌ Problem: "JARVIS.exe has stopped working"
- ✅ Solution: পুরো `dist\JARVIS` folder copy করেছেন কিনা check করুন

### ❌ Problem: "API key not configured"
- ✅ Solution: `config\api_keys.json` file এ সঠিক key বসিয়েছেন কিনা দেখুন

### ❌ Problem: "Microphone not working"
- ✅ Solution: Settings → Audio Devices থেকে সঠিক microphone select করুন

### ❌ Problem: Slow cold-start
- ✅ Normal: প্রথমবার খুলতে 5-10 সেকেন্ড লাগতে পারে
- ✅ পরেরবার instant হবে

---

## 🎉 সব কিছু ঠিক থাকলে

JARVIS UI খুলে গেলে আপনি:
- 🗣️ Voice দিয়ে command দিতে পারবেন
- ⌨️ Text লিখেও command দিতে পারবেন
- 📱 Phone থেকে remote control করতে পারবেন (QR code scan করে)
- 🎨 Theme, voice, name সব customize করতে পারবেন

**Enjoy your personal JARVIS! 🤖✨**
