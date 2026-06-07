-- [분석 1-1] IT 채용공고 별 학력 요구사항 분포 (예정자 통합 및 정규 순서 정렬)
SELECT 
    CASE 
        WHEN education LIKE '%무관%' THEN '0. 학력무관'
        WHEN education LIKE '%고등학교%' THEN '1. 고등학교 졸업 이상'
        WHEN education LIKE '%대학졸업(2,3년)%' THEN '2. 대학졸업(2,3년) 이상'
        WHEN education LIKE '%대학교졸업(4년)%' THEN '3. 대학교졸업(4년) 이상'
        WHEN education LIKE '%석사%' THEN '4. 석사졸업 이상'
        WHEN education LIKE '%박사%' THEN '5. 박사졸업 이상'
        ELSE '6. 기타'
    END AS `학력_요구사항`,
    COUNT(*) as job_count
FROM jumpit_processed_jobs
GROUP BY 
    CASE 
        WHEN education LIKE '%무관%' THEN '0. 학력무관'
        WHEN education LIKE '%고등학교%' THEN '1. 고등학교 졸업 이상'
        WHEN education LIKE '%대학졸업(2,3년)%' THEN '2. 대학졸업(2,3년) 이상'
        WHEN education LIKE '%대학교졸업(4년)%' THEN '3. 대학교졸업(4년) 이상'
        WHEN education LIKE '%석사%' THEN '4. 석사졸업 이상'
        WHEN education LIKE '%박사%' THEN '5. 박사졸업 이상'
        ELSE '6. 기타'
    END
ORDER BY `학력_요구사항` ASC;

-- [분석 1-2] IT 채용공고 별 경력 요구사항 분포 (연차별 그룹화)
SELECT 
    CASE 
        WHEN career LIKE '%무관%' THEN '0. 경력무관'
        WHEN career LIKE '%신입%' THEN '1. 신입'
        WHEN CAST(regexp_extract(career, '([0-9]+)', 1) AS INT) <= 3 THEN '2. 주니어 (~3년)'
        WHEN CAST(regexp_extract(career, '([0-9]+)', 1) AS INT) <= 7 THEN '3. 미들 (4~7년)'
        WHEN CAST(regexp_extract(career, '([0-9]+)', 1) AS INT) <= 10 THEN '4. 시니어 (8~10년)'
        ELSE '5. 리드/디렉터 (11년 이상)'
    END AS `경력_요구사항`,
    COUNT(*) as job_count
FROM jumpit_processed_jobs
GROUP BY 
    CASE 
        WHEN career LIKE '%무관%' THEN '0. 경력무관'
        WHEN career LIKE '%신입%' THEN '1. 신입'
        WHEN CAST(regexp_extract(career, '([0-9]+)', 1) AS INT) <= 3 THEN '2. 주니어 (~3년)'
        WHEN CAST(regexp_extract(career, '([0-9]+)', 1) AS INT) <= 7 THEN '3. 미들 (4~7년)'
        WHEN CAST(regexp_extract(career, '([0-9]+)', 1) AS INT) <= 10 THEN '4. 시니어 (8~10년)'
        ELSE '5. 리드/디렉터 (11년 이상)'
    END
ORDER BY `경력_요구사항` ASC;

-- [분석 2-1] 전통 코딩 스킬 비중 vs AI 스킬 요구량 비교
SELECT 
    COUNT(DISTINCT job_id) as total_jobs,
    COUNT(DISTINCT CASE WHEN has_trad_skill = true THEN job_id END) as trad_required_jobs,
    COUNT(DISTINCT CASE WHEN has_ai_skill = true THEN job_id END) as ai_required_jobs,
    ROUND(COUNT(DISTINCT CASE WHEN has_ai_skill = true THEN job_id END) / COUNT(DISTINCT job_id) * 100, 2) as ai_ratio_percentage
FROM jumpit_processed_jobs;

-- [분석 2-2-1] 전통 코딩 분야 세부 기술 스택 TOP 5
SELECT trad_stack as `전통_기술스택`, COUNT(*) as `공고_수`
FROM jumpit_processed_jobs
LATERAL VIEW explode(tech_stacks_array) t AS trad_stack
WHERE has_trad_skill = true 
  AND lower(trad_stack) IN ('r', 'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'c', 'go', 'kotlin', 'swift', 'php', 'html', 'css', 'spring', 'spring boot', 'react', 'node.js', 'vue.js', 'next.js', 'express', 'django', 'fastapi', 'flask', 'wpf', 'mysql', 'postgresql', 'oracle', 'mariadb', 'mongodb', 'redis', 'aws', 'docker', 'kubernetes', 'linux', 'git', 'github')
GROUP BY trad_stack
ORDER BY `공고_수` DESC
LIMIT 5;

-- [분석 2-2-2] AI 분야 세부 기술 스택 TOP 5
SELECT ai_stack as `AI_기술스택`, COUNT(*) as `공고_수`
FROM jumpit_processed_jobs
LATERAL VIEW explode(tech_stacks_array) t AS ai_stack
WHERE has_ai_skill = true 
  AND lower(ai_stack) NOT IN ('python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'c', 'go', 'kotlin', 'swift', 'php', 'html', 'css', 'spring', 'spring boot', 'react', 'node.js', 'vue.js', 'next.js', 'express', 'django', 'fastapi', 'flask', 'wpf', 'mysql', 'postgresql', 'oracle', 'mariadb', 'mongodb', 'redis', 'aws', 'docker', 'kubernetes', 'linux', 'git', 'github', 'r', '')
GROUP BY ai_stack
ORDER BY `공고_수` DESC
LIMIT 5;

-- [분석 3] IT기업 우대사항
SELECT 
    COUNT(*) as `총_공고_수`,
    SUM(CASE WHEN has_experience_required = true THEN 1 ELSE 0 END) as `경험_요구_건수`,
    ROUND(SUM(CASE WHEN has_experience_required = true THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) as `경험_요구_비율_퍼센트`,
    SUM(CASE WHEN has_collaboration_required = true THEN 1 ELSE 0 END) as `협업_요구_건수`,
    ROUND(SUM(CASE WHEN has_collaboration_required = true THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) as `협업_요구_비율_퍼센트`,
    SUM(CASE WHEN has_ai_relation_required = true THEN 1 ELSE 0 END) as `AI_관련_요구_건수`,
    ROUND(SUM(CASE WHEN has_ai_relation_required = true THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) as `AI_요구_비율_퍼센트`
FROM jumpit_processed_jobs;