/**
 * 📤 커밋 메시지에서 키워드(HYU, HYU-12, HYU-12-m)와 본문을 추출
 * 
 * ✅ 맨 앞 또는 맨 뒤에 위치한 키워드 인식
 * ✅ 둘 다 있을 경우 '맨 앞' 키워드를 우선 처리
 *
 * @param commitMsg 커밋 메시지 전체
 * @returns { key: string | null, message: string } 추출 결과
 */
export function extractIssueData(commitMsg: string): { key: string | null, message: string } {
    const frontRegex = /^\s*(HYU(?:-\d+(?:-m)?)?)\b\s+(.*)$/;
    const backRegex = /^(.*\S)\s+(HYU(?:-\d+(?:-m)?)?)\s*$/;
  
    let key: string | null = null;
    let message: string = commitMsg.trim();
  
    const frontMatch = commitMsg.match(frontRegex);
    if (frontMatch) {
      key = frontMatch[1];
      message = frontMatch[2].trim();
      return { key, message };
    }
  
    const backMatch = commitMsg.match(backRegex);
    if (backMatch) {
      key = backMatch[2];
      message = backMatch[1].trim();
      return { key, message };
    }
  
    return { key: null, message };
  }
  