import { LinearClient } from "@linear/sdk";

async function test() {
  const accessToken = process.env.LINEAR_ACCESS_TOKEN!;
  const linear = new LinearClient({ accessToken });

  const teams = await linear.teams();
  const team = teams.nodes.find((t) => t.name === "Hyundairotem_ai2");

  if (!team) throw new Error("팀 못 찾음");

  const response = await linear.client.request(
    `
    mutation CreateIssue($input: IssueCreateInput!) {
      issueCreate(input: $input) {
        issue {
          id
          identifier
        }
      }
    }
    `,
    {
      input: {
        teamId: team.id,
        title: "테스트 이슈 (GraphQL)",
        description: "SDK create 안 될 때 대비한 GraphQL 생성 방식 테스트",
      },
    }
  );

  console.log("✅ 새 이슈 생성됨:", response.issueCreate.issue.identifier);
}

test().catch(console.error);
