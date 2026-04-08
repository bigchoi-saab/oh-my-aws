# CDK 연계 프로토콜

인시던트 완화 후 CLI로 적용한 변경을 CDK 코드로 영구 반영하는 프로세스.

## Step 1: CDK 반영 제안
```
"인시던트 완화 조치가 CLI로 적용되었습니다.
변경 내용: {cdk_fix_details}

이 변경을 CDK 코드로 영구 반영할까요?
(CDK 반영 없이 종료하면 인프라 drift가 발생합니다)"
```

## Step 2: CDK 프로젝트 탐색
사용자가 승인하면, 먼저 프로젝트 내 CDK 코드 위치를 파악한다:
```bash
# cdk.json 위치 탐색
find . -name "cdk.json" -not -path "*/node_modules/*" -not -path "*/_research/*"
```

## Step 3: CDK Analyzer 배정
CDK Analyzer agent를 생성하여 코드 분석을 수행한다.
```
대기: cdk-analysis.yaml 생성 완료
```

## Step 4: CDK 변경 승인 게이트
cdk-analysis.yaml을 읽어 변경 영향을 확인하고 사용자 승인을 요청한다.
```
"CDK 코드 분석 결과:
 대상 스택: {target_stack}
 변경 내용: {required_change}
 영향 범위: {impact_assessment}

 CDK 코드 수정을 진행할까요?"
```

## Step 5: CDK Engineer 배정
CDK Engineer agent를 생성하여 코드를 수정한다.
```
대기: cdk-changes.yaml 생성 완료
```

## Step 6: Deploy 승인 (항상 HIGH Risk)
cdk-changes.yaml을 읽어 diff 결과를 사용자에게 제시한다.
```
"⚠️ CDK Deploy 승인 요청

 cdk diff 결과:
 {cdk_diff_output}

 수정 파일:
 {files_modified}

 이 변경을 배포할까요? (Y/N)"
```

배포 승인 시 CDK Engineer에게 deploy를 별도 지시하거나, 사용자에게 deploy 명령어를 안내한다.

## Step 7: CDK Reporter 배정
Reporter agent를 생성하여 CDK 변경 감사 보고서를 작성한다.
```
대기: cdk-report.yaml 생성 완료
```
