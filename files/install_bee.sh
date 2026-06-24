#!/bin/bash
#
# 🐝 Spelling Bee Installer
# Run this once to set up the 'bee' command.
#
# What this does:
#   1. Makes scripts executable
#   2. Adds a 'bee' command to your shell (via ~/.zshrc)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHELL_RC="$HOME/.zshrc"

echo ""
echo "🐝 Spelling Bee Installer"
echo "========================="
echo ""

# ── 1. Make scripts executable ─────────────────────────────────────────────────
echo "Step 1/2 — Making scripts executable..."
chmod +x "$SCRIPT_DIR/bee_sync.sh"
chmod +x "$SCRIPT_DIR/install_bee.sh"
echo "         ✓ Done"
echo ""

# ── 2. Add 'bee' alias + helper commands to shell ──────────────────────────────
echo "Step 2/2 — Adding 'bee' command to your shell..."

ALIAS_BLOCK="
# ── Spelling Bee shortcuts ──────────────────────────────────────────────────
alias bee='$SCRIPT_DIR/bee_sync.sh'
alias bee-force='$SCRIPT_DIR/bee_sync.sh --force'
alias bee-status='$SCRIPT_DIR/bee_sync.sh --status'
# ───────────────────────────────────────────────────────────────────────────"

if grep -q "Spelling Bee shortcuts" "$SHELL_RC" 2>/dev/null; then
    echo "         ℹ️  Shell aliases already present in $SHELL_RC, skipping"
else
    echo "$ALIAS_BLOCK" >> "$SHELL_RC"
    echo "         ✓ Added to $SHELL_RC"
    echo "         ✓ Commands available after: source ~/.zshrc (or open a new terminal)"
fi
echo ""

# ── Summary ────────────────────────────────────────────────────────────────────
echo "========================="
echo "✅ Installation complete!"
echo ""
echo "   Commands:"
echo "     bee             — smart sync (save if revealed or GN4L, remind otherwise)"
echo "     bee --force     — save all puzzles with any progress"
echo "     bee --status    — preview what would happen without making changes"
echo ""
echo "   Run 'source ~/.zshrc' or open a new terminal to use 'bee' now."
echo ""
