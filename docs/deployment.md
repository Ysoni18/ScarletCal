# Put ScarletCal online: step by step

You will use two services:

- **Render** runs the Python code that makes calendar files.
- **GitHub Pages** hosts the website people visit.

You do not need to buy a domain. Your website address will be
https://ysoni18.github.io/ScarletCal/ once setup succeeds.

**Current status:** this release includes the Phase 9 deployment files. Hosting
is not configured yet. Start by checking GitHub in Step 1; if the files are
already there, skip the upload commands.

## 1. Upload the latest code to GitHub

First, open [your repository](https://github.com/Ysoni18/ScarletCal). If you can
see `render.yaml` and the **Tests** workflow under **Actions**, the upload is
already done: skip the commands below and check the latest Tests run.

Otherwise, open Terminal on your Mac. Run these commands one at a time:

```bash
cd /Users/yakshsoni/Documents/ChatGPT/ScarletCal
git add -A
git commit -m "Prepare Phase 9 deployment and hardening"
git push origin main
```

These commands save and upload the current project changes. If a command reports
an error, stop and share the error here. You can also ask me to do this step.

Then:

1. Open [your GitHub repository](https://github.com/Ysoni18/ScarletCal).
2. Click **Actions** at the top.
3. Open the newest **Tests** run.
4. Wait for a green check mark. If it fails, stop here and share the failed step.

## 2. Set up Render

1. Open [Render](https://dashboard.render.com/).
2. Create an account or sign in. Connecting with GitHub is convenient.
3. Click **New + → Blueprint**. If you are on the Blueprints page, use
   **New Blueprint Instance** instead.
4. Connect your GitHub account if asked. Give Render access to **ScarletCal**.
5. Select **Ysoni18/ScarletCal**.
6. Use branch **main**. If asked for the file path, enter **render.yaml**.
7. If asked for a Blueprint name, enter **ScarletCal**.
8. Review the proposed service: **scarletcal-api**, with plan **Free**.
   The settings are already filled in by the file we prepared.
9. Click **Deploy Blueprint** and wait for the service to finish deploying.

If Render proposes a paid plan, do not select it just to follow this guide.
Share that screen's message so we can adjust the setup.

## 3. Copy and check your Render address

1. Open the **scarletcal-api** service in Render.
2. Find its web address ending in **.onrender.com** and copy it.
   Keep this address handy for Step 5.
3. Open that address in a new tab with **/healthz** added to the end.

For example, if Render gives you `https://scarletcal-api-abc.onrender.com`, open:

```text
https://scarletcal-api-abc.onrender.com/healthz
```

That address is only an example. Use the one Render actually gives you.

You should see:

```json
{"status":"ok"}
```

That means the calendar generator is running. If it does not appear, finish
fixing the Render deployment before continuing.

## 4. Turn on GitHub Pages

1. Return to [your repository](https://github.com/Ysoni18/ScarletCal).
2. Click **Settings** at the top.
3. Click **Pages** in the left sidebar.
4. Under **Build and deployment**, set **Source** to **GitHub Actions**.

You do not need to choose a template or create another workflow file.

## 5. Tell the website where the calendar generator is

Still in your repository's **Settings**:

1. In the left sidebar, open **Secrets and variables → Actions**.
2. Select the **Variables** tab.
3. Click **New repository variable**.
4. In **Name**, paste exactly:

   ```text
   SCARLETCAL_API_ORIGIN
   ```

5. In **Value**, paste the Render address from Step 3. Start with `https://`
   and end with `.onrender.com`. Leave off `/healthz` and any trailing slash.
6. Click **Add variable**.

Use **Variables**, not **Secrets**. This is a public server address, not a password.

## 6. Publish the website

1. Click the repository's **Actions** tab.
2. Select **Deploy frontend to GitHub Pages** in the left sidebar.
3. Click **Run workflow**.
4. Select branch **main** and click the green **Run workflow** button.
5. Wait for that run to finish with a green check mark.

If the workflow is missing, check that Step 1 uploaded the Phase 9 files to main.
If it fails, open the run and share the failed step's error.

## 7. Test your live website

1. Open [ScarletCal](https://ysoni18.github.io/ScarletCal/).
2. Confirm that the page has its normal colors and layout.
3. Click **Load example**.
4. Choose **Fall 2026**.
5. Check the box confirming the standard full-term calendar.
6. Click **Generate calendar**.
7. Confirm that a file downloads and the page says **140 class events across 4 courses**.

If the free Render service is waking up, the first attempt may time out.
Open its `/healthz` address, wait for the OK message, then try again.

Once this test passes, you can share the GitHub Pages address. Buying a custom
domain can wait.

## When you change the code later

1. Commit and push the changes to GitHub, then wait for **Tests** to pass.
2. If the Python code or semester data changed, open the Render service and use
   **Manual Deploy → Deploy latest commit**. Automatic backend deployment is off.
3. If the website changed, repeat Step 6 to publish it on GitHub Pages.
4. Repeat the sample test in Step 7.

## More information

- [Production details and remaining verification](production-notes.md)
- [Render Blueprint instructions](https://render.com/docs/infrastructure-as-code)
- [GitHub Pages setup](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [GitHub repository variables](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-variables)
- [Running a workflow](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)
