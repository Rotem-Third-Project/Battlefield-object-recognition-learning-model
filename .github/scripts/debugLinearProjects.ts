import { LinearClient } from "@linear/sdk";

// 🔐 환경변수에서 토큰 가져오기
const accessToken = process.env.LINEAR_ACCESS_TOKEN!;
const linear = new LinearClient({ accessToken });

async function main() {
  console.log("📦 Linear 프로젝트 목록 조회 중...");

  // 전체 프로젝트 리스트 가져오기
  const projects = await linear.projects();

  console.log(`🔍 총 ${projects.nodes.length}개의 프로젝트가 감지되었습니다:\n`);
  for (const project of projects.nodes) {
    console.log(`- 📁 ${project.name} (상태: ${project.state}, ID: ${project.id})`);
  }

  console.log("\n✅ 프로젝트 목록 출력 완료");
}

main().catch((err) => {
  console.error("❌ 오류 발생:", err.message);
  process.exit(1);
});
