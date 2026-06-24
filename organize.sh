#!/usr/bin/env bash
# organize.sh — Run this ONCE to finish the file reorganization.
# It moves PDFs to data/knowledge_base/, renames them cleanly,
# archives old static assets, and removes the now-redundant chat1.py / chat2.py.
#
# Usage:
#   cd dakikobo/
#   chmod +x organize.sh
#   ./organize.sh

set -e  # Exit immediately on any error

SRC="Data/New Folder With Items"
DEST="data/knowledge_base"

echo "=== DakiKobo File Reorganization ==="

# 1. Move and rename PDFs into data/knowledge_base/
echo ""
echo "1. Moving and renaming PDFs → $DEST/"

mv "$SRC/Burkina-Faso-Climate-Smart-Agriculture-Investment-Plan.pdf" \
   "$DEST/csa_investment_plan_burkina_final.pdf"

mv "$SRC/Climate-Smart-Agriculture-Investment-Plan-for-Burkina-Faso-Draft-for-Decision-Meeting.pdf" \
   "$DEST/csa_investment_plan_burkina_draft.pdf"

mv "$SRC/BurkinaFaso-State-of-climate-change-adaptation-and-mitigation-efforts.pdf" \
   "$DEST/burkina_climate_adaptation_state_report.pdf"

mv "$SRC/farmerbook.pdf" \
   "$DEST/farmer_training_manual.pdf"

mv "$SRC/i3760e.pdf" \
   "$DEST/fao_publication_i3760e.pdf"

mv "$SRC/editor,+Journal+Editor,+JAA_6596_R1_20210308_V1.pdf" \
   "$DEST/jaa_agronomy_article_2021.pdf"

# These two have cryptic names — renamed to needs_review until you identify them
mv "$SRC/CD5C7E769473.pdf" \
   "$DEST/needs_review_01.pdf"

mv "$SRC/document.pdf" \
   "$DEST/needs_review_02.pdf"

echo "   Done. Old 'Data/' folder is now empty."
rmdir "$SRC" 2>/dev/null && rmdir "Data" 2>/dev/null || true

# 2. Move user avatar to static/images/
echo ""
echo "2. Moving active static assets to static/images/"
mv "static/user.png" "static/images/user_avatar.png" 2>/dev/null || true

# 3. Archive the _old static assets
echo ""
echo "3. Archiving old static assets → static/_archive/"
mv "static/user_old.png"      "static/_archive/" 2>/dev/null || true
mv "static/interface_old.png" "static/_archive/" 2>/dev/null || true
mv "static/logo_old.png"      "static/_archive/" 2>/dev/null || true
mv "static/robot_old.png"     "static/_archive/" 2>/dev/null || true

# 4. Archive the broken.html template
echo ""
echo "4. Archiving templates/broken.html → static/_archive/"
mv "templates/broken.html"    "static/_archive/" 2>/dev/null || true

# 5. Remove original chat1.py / chat2.py now that core/ replacements exist
echo ""
echo "5. Removing legacy source files (replaced by core/)"
rm -f chat1.py chat2.py

echo ""
echo "=== Done! Your project is now organized. ==="
echo ""
echo "Reminder: rename needs_review_01.pdf and needs_review_02.pdf"
echo "once you identify what those documents are."
