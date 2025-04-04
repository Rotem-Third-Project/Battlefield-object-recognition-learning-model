import { LinearClient } from "@linear/sdk";
import { execSync } from "child_process";

async function main() {
  const accessToken = process.env.LINEAR_ACCESS_TOKEN!;
  const linear = new LinearClient({ accessToken });

  const title = execSync("git log -1 --pretty=%s").toString().trim();
  const description = execSync("git log -1 --pretty=%b").toString().trim();

  const teams = await linear.teams();
  const team = teams.nodes.find((t) => t.name === "Hyundairotem_ai2");
  if (!team) throw new Error("팀을 찾을 수 없습니다.");

  // ✅ 수정된 부분
  await linear.issues.create({
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
