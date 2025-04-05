import { LinearClient } from "@linear/sdk";
import { execSync } from "child_process";

async function main() {
  const accessToken = process.env.LINEAR_ACCESS_TOKEN!;
  const linear = new LinearClient({ accessToken });

  const title = execSync("git log -1 --pretty=%s").toString().trim();
  const description = execSync("git log -1 --pretty=%b").toString().trim();

  const teams = await linear.teams();
  const team = teams.nodes.find((t) => t.name === "Hyundairotem_ai2");
  if (!team) {
    throw new Error("❌ Linear 팀 'Hyundairotem_ai2'을 찾을 수 없습니다.");
  }

  const issueIdMatch = title.match(/([A-Z]+-\d+)/);
  const issueIdentifier = issueIdMatch?.[1];

  if (!issueIdentifier) {
    console.log("⚠️ 이슈 키를 찾을 수 없습니다. 새 이슈를 생성합니다.");

    const newIssue = await linear.issues.create({
      teamId: team.id,
      title,
      description,
    });

    console.log(`✅ 새 이슈가 생성되었습니다: ${newIssue.issue.identifier}`);
    return;
  }

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

  if (!parentIssue) {
    console.log(
      `⚠️ '${issueIdentifier}' 키에 해당하는 이슈를 찾을 수 없습니다. 새 이슈를 생성합니다.`
    );

    const newIssue = await linear.issues.create({
      teamId: team.id,
      title,
      description,
    });

    console.log(`✅ 새 이슈가 생성되었습니다: ${newIssue.issue.identifier}`);
    return;
  }

  if (title.startsWith("fix:")) {
    await linear.issueCommentCreate({
      issueId: parentIssue.id,
      body: `🔧 **Fix 커밋 감지됨**\n\n**제목:** ${title}\n\n**내용:**\n${description}`,
    });

    console.log(`✅ '${issueIdentifier}'에 댓글이 추가되었습니다.`);
  } else if (title.startsWith("feat:")) {
    await linear.issues.create({
      teamId: team.id,
      parentId: parentIssue.id,
      title,
      description,
    });

    console.log(`✅ '${issueIdentifier}'의 서브이슈가 생성되었습니다.`);
  } else {
    console.log("ℹ️ fix: 또는 feat: 커밋이 아니므로 처리하지 않습니다.");
  }
}

main().catch((e) => {
  console.error("❌ 실행 중 오류 발생:", e);
  process.exit(1);
});
