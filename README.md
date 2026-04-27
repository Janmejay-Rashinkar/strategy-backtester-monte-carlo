# HTF Rejection & Monte Carlo Backtester

An AI-powered Streamlit dashboard for backtesting a high-probability trading strategy based on **EMA 200 Rejection** and **M15 Retracement** logic.

##  The Strategy
1. **HTF Rejection:** Identify price rejection at key levels (EMA 200, S/R) on H1/H4 timeframes.
2. **Volume Confirmation:** Look for institutional activity in the direction of rejection.
3. **M15 Entry:** Fine-tune entry on a 30-50% retracement.
4. **Risk Management:** Dynamic Stop Loss using ATR and Monte Carlo simulations to assess account longevity.

##  How to Run
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   Run the app:

Bash
streamlit run stratergygpt.py
Mission accomplished! You’ve officially pushed your code to GitHub. That "main -> main" and "branch 'main' set up to track..." message is exactly what we wanted to see.

Your strategy-backtester-monte-carlo repository is now live and public.

What did you just upload?
Based on the "Enumerating objects: 4" part of your message, you likely pushed:

stratergygpt.py

requirements.txt

.gitignore

(Possibly a hidden folder or a small data file if it wasn't ignored)

One final touch: The README
Right now, if someone visits your GitHub profile, they’ll see the code, but they won't know how to run it or what the strategy actually does. We should add a README.md file.

You can create this directly in VS Code just like you did with the other files. Here is a professional template you can use:

File Name: README.md
Content:

Markdown
# HTF Rejection & Monte Carlo Backtester

An AI-powered Streamlit dashboard for backtesting a high-probability trading strategy based on **EMA 200 Rejection** and **M15 Retracement** logic.

##  The Strategy
1. **HTF Rejection:** Identify price rejection at key levels (EMA 200, S/R) on H1/H4 timeframes.
2. **Volume Confirmation:** Look for institutional activity in the direction of rejection.
3. **M15 Entry:** Fine-tune entry on a 30-50% retracement.
4. **Risk Management:** Dynamic Stop Loss using ATR and Monte Carlo simulations to assess account longevity.

##  How to Run
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
Run the app:

Bash
streamlit run stratergygpt.py

 Tech Stack
Python (Pandas, NumPy)

Streamlit (UI/UX)

Matplotlib (Visualization)


### To update your GitHub with this new file:
Once you save the `README.md` in VS Code, run these three commands to "sync" it to the internet:
```bash
git add README.md
git commit -m "Add README with strategy documentation"
git push