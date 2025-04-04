// .github/scripts/createLinearDraft.ts
import { LinearClient } from "@linear/sdk";
import fetch from "node-fetch";

// Git 환경에서 실행되므로, child_process로 커밋 메시지 읽음
import { execSync } from "child_process";

async function main() {
  const clientId = process.env.LINEAR_CLIENT_ID!;
  const clientSecret = process.env.LINEAR_CLIENT_SECRET!;

  // ✅ OAuth2 Client Credentials 방식으로 Access Token 발급
  const response = await fetch("https://api.linear.app/oauth/token", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      grant_type: "client_credentials",
      client_id: clientId,
      client_secret: clientSecret,
    }),
  });

  const tokenData = await response.json();
  const accessToken = tokenData.access_token;

  const linear = new LinearClient({ accessToken });

  // 최신 커밋 메시지 가져오기
  const title = execSync("git log -1 --pretty=%s").toString().trim();
  const description = execSync("git log -1 --pretty=%b").toString().trim();

  // 팀 이름 → 팀 ID 조회
  const teams = await linear.teams();
  const team = teams.nodes.find((t) => t.name === "Hyundairotem_ai2"); // 팀 이름 정확히 입력

  if (!team) {
    throw new Error("팀을 찾을 수 없습니다.");
  }

  // Draft 이슈 생성
  await linear.issueCreate({
    teamId: team.id,
    title,
    description,
    draft: true,
  });

  console.log("✅ Linear Draft 이슈가 생성되었습니다!");
}

main().catch((e) => {
  console.error("❌ 오류:", e);
  process.exit(1);
});