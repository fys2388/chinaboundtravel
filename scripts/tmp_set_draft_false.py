# 临时脚本：两篇新发页 front-matter draft:false + audit_status pass2（用完即删）
import pathlib, re
for f in [
    "content/posts/kung-fu-and-martial-arts-in-china-where-to-see-and-train-guide.md",
    "content/posts/china-solo-travel-guide-safety-hostels-and-making-friends.md",
]:
    p = pathlib.Path(f)
    t = p.read_text(encoding="utf-8")
    before = t
    t = re.sub(r'(?m)^draft:\s*"?true"?\s*$', 'draft: false', t)
    t = re.sub(r'(?m)^audit_status:\s*"?pending"?\s*$', 'audit_status: "pass2"', t)
    p.write_text(t, encoding="utf-8")
    print("changed:", f, "|", t != before)
