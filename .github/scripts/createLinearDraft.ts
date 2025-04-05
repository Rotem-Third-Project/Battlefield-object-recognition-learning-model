import { LinearClient } from "@linear/sdk";
import { execSync } from "child_process";

async function main() {
  const accessToken = process.env.LINEAR_ACCESS_TOKEN!;
  const linear = new LinearClient({ accessToken });

  // 최근 커밋의 제목과 본문 가져오기
  const title = execSync("git log -1 --pretty=%s").toString().trim();
  const description = execSync("git log -1 --pretty=%b").toString().trim();

  // Linear 팀 정보 확인
  const teams = await linear.teams();
  const team = teams.nodes.find((t) => t.name === "Hyundairotem_ai2"); // ← 팀 이름 확인 필요
  if (!team)
    throw new Error("❌ Linear 팀 'Hyundairotem_ai2'을 찾을 수 없습니다.");

  // 커밋 메시지에서 이슈 키 (예: ENG-123) 추출
  const issueIdMatch = title.match(/([A-Z]+-\d+)/);
  const issueIdentifier = issueIdMatch?.[1];

  // 이슈 키가 없는 경우 → 새 이슈 생성
  if (!issueIdentifier) {
    console.log("⚠️ 이슈 키를 찾을 수 없습니다. 새 이슈를 생성합니다.");

    const newIssue = await linear.issueCreate({
      teamId: team.id,
      title,
      description,
    });

    console.log(`✅ 새 이슈가 생성되었습니다: ${newIssue.issue.identifier}`);
    return;
  }

  // 🔍 이슈 키로 기존 이슈 검색
  const searchResult = await linear.client.request(
    `
    query SearchIssues($term: String!) {
      searchIssues(term: $term) {
        nodes {
          id
          title
        }
      }
    }
  `,
    { term: issueIdentifier }
  );

  const parentIssue = searchResult.searchIssues.nodes[0];

  // 이슈가 존재하지 않으면 → 새 이슈 생성
  if (!parentIssue) {
    console.log(
      `⚠️ '${issueIdentifier}' 키에 해당하는 이슈를 찾을 수 없습니다. 새 이슈를 생성합니다.`
    );

    const newIssue = await linear.issueCreate({
      teamId: team.id,
      title,
      description,
    });

    console.log(`✅ 새 이슈가 생성되었습니다: ${newIssue.issue.identifier}`);
    return;
  }

  // 🔧 fix: → 댓글 추가
  if (title.startsWith("fix:")) {
    await linear.issueCommentCreate({
      issueId: parentIssue.id,
      body: `🔧 **Fix 커밋 감지됨**\n\n**제목:** ${title}\n\n**내용:**\n${description}`,
    });

    console.log(`✅ '${issueIdentifier}'에 댓글이 추가되었습니다.`);
  }

  // ✨ feat: → 서브이슈 생성
  else if (title.startsWith("feat:")) {
    await linear.issueCreate({
      teamId: team.id,
      parentId: parentIssue.id,
      title,
      description,
    });

    console.log(`✅ '${issueIdentifier}'의 서브이슈가 생성되었습니다.`);
  }

  // 기타 커밋 → 무시
  else {
    console.log("ℹ️ fix: 또는 feat: 커밋이 아니므로 처리하지 않습니다.");
  }
}

main().catch((e) => {
  console.error("❌ 실행 중 오류 발생:", e);
  process.exit(1);
});
