# 🤖 Fully Automated Spelling Bee Update

## Option 1: Keyboard Shortcut (Recommended - 10 seconds total)

### One-Time Setup:

1. **Open Shortcuts app** on Mac (in Applications or search with Cmd+Space)

2. **Create new Shortcut**, paste this:

**Shortcut Actions:**
```
1. Run Shell Script:
   Shell: /bin/bash
   Input: (none)
   Script:

   cd ~/Desktop/spelling-bee-analytics/files
   ./update_spelling_bee.sh

2. Show Notification:
   Title: ✅ Spelling Bee Updated
   Body: Your analytics database has been updated!
```

3. **Name it:** "Update Spelling Bee"

4. **Assign keyboard shortcut:** (Settings → Click shortcut → Add Keyboard Shortcut)
   - Suggested: `⌃⌥B` (Control+Option+B for "Bee")

### Daily Use:
1. Play Spelling Bee
2. Click bookmarklet → downloads to ~/Downloads
3. Press `⌃⌥B` → notification appears when done!

---

## Option 2: Menu Bar Shortcut (Visual)

Same as above, but also:
- In Shortcuts app: Right-click shortcut → Add to Menu Bar
- Now you have a 🐝 icon in your menu bar
- Click it anytime to run the update

---

## Option 3: Auto-Run When File Appears (Fully Automated)

### Using Automator Folder Action:

1. **Open Automator** (in Applications)

2. **New Document → Folder Action**

3. **"Folder Action receives files and folders added to:"**
   - Select: `Downloads`

4. **Add Action: "Run Shell Script"**
   ```bash
   # Check if the added file is spelling_bee_raw.json
   for f in "$@"
   do
       if [[ "$(basename "$f")" == "spelling_bee_raw.json" ]]; then
           # Run the update script
           cd ~/Desktop/spelling-bee-analytics/files
           ./update_spelling_bee.sh

           # Show notification
           osascript -e 'display notification "Your analytics database has been updated!" with title "✅ Spelling Bee Updated"'
       fi
   done
   ```

5. **Save as:** "Spelling Bee Auto Update"

### Daily Use:
1. Play Spelling Bee
2. Click bookmarklet
3. **That's it!** Notification appears automatically 🎉

---

## Comparison

| Option | Clicks | Automation Level |
|--------|--------|------------------|
| **Manual** | 3 (bookmarklet + move file + run script) | Basic |
| **Keyboard Shortcut** | 2 (bookmarklet + keyboard) | Good ⭐ |
| **Menu Bar** | 2 (bookmarklet + menu icon) | Good |
| **Folder Action** | 1 (bookmarklet only) | Fully Automated ⭐⭐⭐ |

---

## My Recommendation

**Start with Keyboard Shortcut** (easiest to set up, very fast):
1. Takes 2 minutes to set up
2. Press one key combo after bookmarklet
3. Notification tells you it's done

**Later add Folder Action** if you want zero-click automation:
- Automatically runs when file appears
- Truly hands-free after clicking bookmarklet

---

## Troubleshooting

### If keyboard shortcut doesn't work:
- Open System Settings → Privacy & Security → Automation
- Allow Shortcuts to control Terminal/System Events

### If folder action doesn't trigger:
- Open Automator → Preferences → Enable Folder Actions
- Right-click Downloads folder → Services → Folder Actions Setup
- Make sure your workflow is enabled

### If notification doesn't appear:
- System Settings → Notifications → Allow notifications from Scripts

---

## Even Lazier: Schedule Daily Reminder

Add to Calendar/Reminders:
- "Play Spelling Bee + press ⌃⌥B"
- Repeats daily at your usual play time
- Builds the habit!

