import { LinearClient } from "@linear/sdk";
import { execSync } from "child_process";

async function main() {
  const accessToken = process.env.LINEAR_ACCESS_TOKEN!;
  const linear = new LinearClient({ accessToken });

  const title = execSync("git log -1 --pretty=%s").toString().trim();
  const description = execSync("git log -1 --pretty=%b").toString().trim();

  // 팀 찾기
  const teams = await linear.teams();
  const team = teams.nodes.find((t) => t.name === "Hyundairotem_ai2");
  if (!team)
    throw new Error("❌ Linear 팀 'Hyundairotem_ai2'을 찾을 수 없습니다.");

  // 커밋에서 이슈 키 추출
  const issueIdMatch = title.match(/([A-Z]+-\d+)/);
  const issueIdentifier = issueIdMatch?.[1];

  // 🔍 이슈 키가 없을 경우 → 새 이슈 생성
  if (!issueIdentifier) {
    console.log("⚠️ 이슈 키가 없으므로 새 이슈를 생성합니다.");

    const response = await linear.client.request(
      `
      mutation CreateIssue($input: IssueCreateInput!) {
        issueCreate(input: $input) {
          issue {
            identifier
          }
        }
      }
      `,
      {
        input: {
          teamId: team.id,
          title,
          description,
        },
      }
    );

    console.log(
      `✅ 새 이슈가 생성되었습니다: ${response.issueCreate.issue.identifier}`
    );
    return;
  }

  // 🔍 기존 이슈 검색
  const searchResult = await linear.client.request(
    `
    query SearchIssues($term: String!) {
      searchIssues(term: $term) {
        nodes {
          id
          identifier
        }
      }
    }
    `,
    { term: issueIdentifier }
  );

  const parentIssue = searchResult.searchIssues.nodes[0];

  // 🔧 이슈가 없으면 새로 생성
  if (!parentIssue) {
    console.log(
      `⚠️ '${issueIdentifier}' 이슈가 존재하지 않아 새로 생성합니다.`
    );

    const response = await linear.client.request(
      `
      mutation CreateIssue($input: IssueCreateInput!) {
        issueCreate(input: $input) {
          issue {
            identifier
          }
        }
      }
      `,
      {
        input: {
          teamId: team.id,
          title,
          description,
        },
      }
    );

    console.log(
      `✅ 새 이슈가 생성되었습니다: ${response.issueCreate.issue.identifier}`
    );
    return;
  }

  // 💬 fix: → 댓글 생성
  if (title.startsWith("fix:")) {
    await linear.client.request(
      `
      mutation CreateComment($input: CommentCreateInput!) {
        commentCreate(input: $input) {
          success
        }
      }
      `,
      {
        input: {
          issueId: parentIssue.id,
          body: `🔧 **Fix 커밋 감지됨**\n\n**제목:** ${title}\n\n**내용:**\n${description}`,
        },
      }
    );

    console.log(`✅ '${issueIdentifier}' 이슈에 댓글이 추가되었습니다.`);
  }

  // 🧩 feat: → 서브이슈 생성
  else if (title.startsWith("feat:")) {
    const response = await linear.client.request(
      `
      mutation CreateSubIssue($input: IssueCreateInput!) {
        issueCreate(input: $input) {
          issue {
            identifier
          }
        }
      }
      `,
      {
        input: {
          teamId: team.id,
          parentId: parentIssue.id,
          title,
          description,
        },
      }
    );

    console.log(
      `✅ '${issueIdentifier}'에 서브이슈가 생성되었습니다: ${response.issueCreate.issue.identifier}`
    );
  }

  // 그 외는 무시
  else {
    console.log("ℹ️ fix: 또는 feat: 커밋이 아니므로 처리하지 않습니다.");
  }
}

main().catch((e) => {
  console.error("❌ 실행 중 오류 발생:", e);
  process.exit(1);
});
