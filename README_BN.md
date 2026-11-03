# MONEY PAY — Telegram Referral Mini App (Starter)

এই প্রজেক্টে আছে:
- পাঁচটি চ্যানেলের membership gate ও Verify button
- Telegram Mini App
- ৳৫ referral reward (নতুন referred user পাঁচটি চ্যানেল verify করলে একবার)
- ৳৫০ minimum withdrawal
- bKash/Nagad withdrawal request
- Admin-এর manual approve/reject (`/admin`)

## গুরুত্বপূর্ণ
এটি একটি starter implementation; লাইভে দেওয়ার আগে নিজের hosting-এ পরীক্ষা করুন। Referral earning বাস্তব ব্যবহারকারী ও পরিষ্কার নিয়মের ভিত্তিতে চালান। ভুয়া অ্যাকাউন্ট/স্প্যাম উৎসাহিত করবেন না। পেমেন্ট approve করলে Admin-কে আলাদাভাবে bKash/Nagad-এ টাকা পাঠাতে হবে।

## 1. BotFather
1. `@BotFather` থেকে bot তৈরি করুন।
2. Token গোপন রাখুন; কারও সঙ্গে শেয়ার করবেন না।
3. Bot username লিখে রাখুন।

## 2. চারটি Chat (৩টি Channel + ১টি Group)
- Bot-কে চারটি চ্যাটের প্রতিটিতে Administrator করুন।
- Membership check করার permission থাকতে হবে।
- `.env`-এ প্রতিটি channel-এর numeric ID `-100...` এবং public/invite link বসান।
- Private channel হলে invite link ব্যবহার করুন। ID বের করতে Telegram bot/API tooling লাগতে পারে; ID ভুল হলে verification fail হবে।

## 3. Admin ID
নিজের Telegram numeric user ID বের করে `.env`-এ `ADMIN_ID` দিন। BotFather token কখনো Admin ID নয়।

## 4. Hosting
Python 3.11+ এবং স্থায়ী HTTPS domain-সহ hosting লাগবে। Project upload করে:
```bash
pip install -r requirements.txt
cp .env.example .env
# .env সম্পাদনা করুন
python bot.py
```
Hosting provider-এ process-টি চালু রাখুন। `WEBAPP_URL`-এ এই Flask app-এর HTTPS URL দিন। Telegram Mini App-এর জন্য HTTPS আবশ্যক।

## 5. BotFather Mini App button
BotFather-এ `/setmenubutton` ব্যবহার করে Web App URL সেট করুন, অথবা bot-এর reply keyboard থেকে Open MONEY PAY বাটন ব্যবহার করুন।

## 6. Referral link
Mini App share link-এ `BOT_USERNAME` configure করতে হবে। `templates/index.html`-এ `YOUR_BOT_USERNAME`-এর জায়গায় নিজের username বসান (শুধু @ ছাড়া username)।

## 7. নিরাপত্তা ও সীমাবদ্ধতা
- Token `.env`-এ রাখুন, public repo-তে দেবেন না।
- Bot-কে চারটি channel/group-এ admin না করলে membership check কাজ করবে না।
- বর্তমানে প্রতি referral-এ একবারই reward; self-referral আটকানো আছে। আরও শক্ত anti-fraud (device/IP abuse detection, payout review) production-এ যোগ করুন।
- Withdrawal request ৳৫০ করে নেয়; reject হলে balance ফেরত আসে। Approve মানে request অনুমোদন—টাকা স্বয়ংক্রিয়ভাবে পাঠানো হয় না।
- Privacy policy, terms, support contact এবং স্থানীয় আইন/প্ল্যাটফর্ম নীতি মেনে চালু করুন।
