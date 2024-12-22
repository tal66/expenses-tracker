# Expenses Tracker

Easy-to-use credit expenses downloader, tracker and visualizer, with AI insights.

<img src="app.png" width=500>


## Start

See instructions in the [Install](#install) section, and then:

```bash
python main.py
```

To run DEMO expenses data:

```bash
python main.py demo
```



## Features

One-click to: 
- Download last quarter credit card expenses
- Visualize expenses by categories and months
- Get AI-powered insights

---

Automation:
- Download expenses data from credit card provider (currently only supports 'Max' credit cards)
- App is set to download last quarter files (can be changed in the code)
- Note: you may get different popups than me, and have to alter the code or handle them manually. It runs in ~20 seconds for me (could be faster, but allows the user to see what's happening, and the site to load)

UI:
- Expense category analysis with bar and pie charts
- Monthly totals visualization
- Detailed transactions table
- Monthly filtering

AI Insights:
- Summary
- Suggestions and insights


## Install

Fill in credit card credentials in `config.toml`, and optionally add Gemini API key,  
and user background in `expenses_tracker/data/user_background.txt`.
Then:

```bash
pip install -e .
```

```bash
playwright install
```

## Legal

This is a hobby project 📚 and the developer does not profit from its use, and is also not affiliated with any credit card provider.

But since this is a project involving financial data and decisions, 
here are some legal notes regarding the use of this software:

<details>
<summary> 
legal notes
</summary>
The developer is not affiliated with any credit card provider, and does not guarantee the accuracy of the data downloaded from the credit card provider. The user is responsible for verifying the data. 

The developer is not affiliated with any AI service suggested in the app and does not guarantee the accuracy of the AI insights.

It is the user's responsibility to keep credentials and data secure on his or her machine only. It is the user's responsibility not to share credentials with anyone, including AI services.

The user may choose to only use the app for visualization and for downloading expenses data automatically, without sharing it with AI services. This way the user can keep his or her data on his or her machine only.

This software is provided as is, without any warranty. The developer is not responsible for any data leaks if the user chooses to share his or her data with AI services. The developer is not a financial advisor, and only the user is responsible for his financial decisions. The developer is not responsible for any kind of damages due to misuse of this software.
</details>

<br/><br/>