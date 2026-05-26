# Coordinator Sample Queries

Use these sample inquiries with the coordinator agent. Five are English and five are
Japanese. Some examples intentionally omit key facts so the coordinator should ask for
clarification before running the specialist investigation.

## English

### 1. Apex Robotics: interview invitation delivery outage

```text
Apex Robotics reports that interview invitation emails are not delivered to all candidates
for a manufacturing hiring event. They are a Premier customer, and recruiting operations
are blocked. Check prior cases, known incidents, SLA, first response, and escalation plan.
```

Expected behavior: ready for investigation.

### 2. BlueWave Health: Google Calendar availability unavailable

```text
BlueWave Health says Google Calendar availability is not showing any free slots for panel
interviewers after the recruiting admin reconnected calendars this morning. Recruiting is
blocked for executive hiring. Check whether this is a known incident or customer-specific.
```

Expected behavior: ready for investigation.

### 3. Unclear candidate email issue

```text
Candidates are not getting emails. Can you check what is going on?
```

Expected behavior: clarification likely.

Suggested reply to the AI:

```text
The affected customer is Apex Robotics. The workflow is interview invitation email delivery.
All candidates for requisition REQ-7842 are affected, and the first failures started today
at 09:20 UTC. This is a Premier customer.
```

### 4. Evergreen Retail: CSV import missing fields

```text
Evergreen Retail imported a CSV for seasonal hiring. The import job IMP-88291 completed,
but candidate phone numbers are blank for about 180 rows. They expected 1,240 candidates
with email and phone fields. Please compare historical tickets, import policy, and next
diagnostic steps.
```

Expected behavior: ready for investigation.

### 5. Ambiguous scheduling problem

```text
Scheduling is broken for one of our customers. They need help today.
```

Expected behavior: clarification likely.

Suggested reply to the AI:

```text
The customer is DeltaHire Studios. The issue is with Google Calendar availability for
panel interviews. Three interviewers show no available slots for requisition REQ-5520.
The first failure was reported yesterday at 16:00 UTC. Business impact is medium because
interviews can be scheduled manually as a workaround.
```

## Japanese

### 6. ClearPath Logistics: 求人ページの応募フォームが表示されない

```text
ClearPath Logistics から、公開中の求人ページで応募フォームが表示されず、候補者が応募できないと連絡がありました。
ドライバー採用キャンペーン中で候補者向けの影響があります。既知インシデントか顧客固有設定か、過去チケット、
SLA、エスカレーション先を確認してください。
```

想定動作: 調査可能。

### 7. DeltaHire Studios: 評価シートの権限不備

```text
DeltaHire Studios で、面接官が評価シートを開くと読み取り専用になり、面接フィードバックを送信できません。
対象は requisition REQ-4408 の final interview stage です。Hiring Manager は今日中に評価を集めたいと言っています。
類似ケース、権限ポリシー、追加で必要な情報を確認してください。
```

想定動作: 調査可能。

### 8. 顧客名がない CSV インポート不具合

```text
CSV インポート後に候補者データが欠落しているようです。原因と復旧方法を調べてください。
```

想定動作: clarification が必要。

AI への返答案:

```text
顧客は Evergreen Retail です。インポートジョブ ID は IMP-88291 で、欠落しているのは候補者の phone number です。
期待件数は 1,240 件、実際に phone number が空欄になった候補者は約 180 件です。CSV のサンプル行は個人情報を
マスクして共有できます。
```

### 9. Apex Robotics: 面接招待メールが一部候補者に届かない

```text
Apex Robotics で、面接招待メールが一部候補者に届いていません。対象は requisition REQ-7842 の候補者 35 名で、
手動再送しても 12 名には届いていないようです。送信テンプレートは interview_panel_invite_v3 です。
過去事例、既知インシデント、Messaging Platform へのエスカレーション要否を確認してください。
```

想定動作: 調査可能。

### 10. 影響範囲が曖昧な求人ページ不具合

```text
求人ページがおかしいと顧客から言われています。急ぎで見てください。
```

想定動作: clarification が必要。

AI への返答案:

```text
顧客は ClearPath Logistics です。公開中の求人ページ JOB-3910 と JOB-3911 で応募フォームが表示されません。
候補者は求人説明は見えますが応募ボタンを押せません。最初に確認したのは今日の 10:15 JST です。
昨日、応募フォームのカスタム質問を変更しました。
```
