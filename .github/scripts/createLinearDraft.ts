import { LinearClient } from "@linear/sdk";
import { execSync } from "child_process";

async function main() {
  const accessToken = process.env.LINEAR_ACCESS_TOKEN!;
  const linear = new LinearClient({ accessToken });

  const title = execSync("git log -1 --pretty=%s").toString().trim(); // 커밋 제목
  const description = execSync("git log -1 --pretty=%b").toString().trim(); // 커밋 본문

  const teams = await linear.teams();
  const team = teams.nodes.find((t) => t.name === "Hyundairotem_ai2");
  if (!team) throw new Error("팀을 찾을 수 없습니다.");

  // 커밋 메시지에 포함된 이슈 ID 추출 예: ENG-123
  const issueIdMatch = title.match(/([A-Z]+-\d+)/);
  const issueIdentifier = issueIdMatch?.[1];

  if (!issueIdentifier) {
    console.log("이슈 키를 찾을 수 없습니다. 이슈와 연결할 수 없습니다.");
    return;
  }

  const searchResult = await linear.searchIssues({ query: issueIdentifier });
  const parentIssue = searchResult.nodes[0];
  if (!parentIssue) {
    console.log("해당 이슈를 찾을 수 없습니다.");
    return;
  }

  if (title.startsWith("fix:")) {
    // fix: → 기존 이슈에 댓글 추가
    await linear.issueCommentCreate({
      issueId: parentIssue.id,
      body: `🔧 Fix 커밋: ${title}\n\n${description}`,
    });

    console.log("✅ 기존 이슈에 fix 댓글이 추가되었습니다.");
  } else if (title.startsWith("feat:")) {
    // feat: → 기존 이슈의 서브이슈 생성
    await linear.issueCreate({
      teamId: team.id,
      parentId: parentIssue.id,
      title,
      description,
    });

    console.log("✅ 서브이슈(feat)가 생성되었습니다.");
  } else {
    console.log("✅ fix: 또는 feat: 커밋이 아니라서 무시됩니다.");
  }
}

main().catch((e) => {
  console.error("❌ 오류:", e);
  process.exit(1);
});
