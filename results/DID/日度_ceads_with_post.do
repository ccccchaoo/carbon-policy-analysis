cd "D:\桌面\sim-degree3.0\results\DID"
sysdir set PLUS "D:\Stata17\ado\plus"
*请选择本地stata环境

*ssc install reghdfe
*ssc install ftools
*ssc install coefplot, replace
*ssc install e
import excel "日度_ceads.xlsx", firstrow clear

*未跟进政策的地方不进入讨论
keep if treated != 0 & !missing(treated)

* 处理policy_time变量
gen policy_group = policy_day
replace policy_group = 0 if missing(policy_group)

* 生成处理变量
gen post = (day >= policy_group & !missing(policy_group))
replace post = 0 if missing(policy_group)

*核心解释变量 treated	SA_att	AS_att	SA_outweight	AS_outweight

gen intensity = SA_att

* ============================================================
* 仅用于输出文件名：记录本次 intensity 使用的变量名
* ============================================================
local intensity_name SA_att

gen did = intensity * post


gen y1 = Aviation碳排值
gen y2 = GroundTransport碳排值
gen y3 = Industry碳排值
gen y4 = Power碳排值
gen y5 = Residential碳排值
gen y = Total碳排值


* ============================================================

* 1. 标记各地区政策发生前30天的基期窗口
gen __pre1m = (policy_group > 0 & day >= policy_group - 30 & day < policy_group)


bysort id: egen group_base_total = mean(cond(__pre1m == 1, Total碳排值, .))

capture confirm variable 碳排强度
if _rc == 0 {
    gen __carbon_intensity = 碳排强度
}
else {
    gen __carbon_intensity = Total碳排值 / 生产总值 if 生产总值 > 0
}
bysort id: egen group_base_ci = mean(cond(__pre1m == 1, __carbon_intensity, .))


gen __power_share = Power碳排值 / Total碳排值 if Total碳排值 > 0
bysort id: egen group_base_power_share = mean(cond(__pre1m == 1, __power_share, .))

bysort id: egen group_base_industry2 = mean(cond(__pre1m == 1, 工业结构, .))

bysort id: egen base_month_n = total(__pre1m == 1)
label variable base_month_n "政策前30天基期窗口观测数"

* 清理临时变量；保留 base_month_n 方便检查基期均值是否由足够观测计算
drop __pre1m __carbon_intensity __power_share

* ============================================================
* 选择本次异质性分组变量：三选一
* 只保留一行 local grouping_var 为启用状态
* ============================================================
local grouping_var group_base_ci
* local grouping_var group_base_ci
* local grouping_var group_base_power_share
* local grouping_var group_base_industry2

gen group = `grouping_var'

* ============================================================
* 分位数：按地区计算，不让同一地区的日度观测重复参与分位点
* ============================================================
preserve
keep id group
bysort id: keep if _n == 1
quietly summarize group, detail
scalar group_p25  = r(p25)
scalar group_p50  = r(p50)
scalar group_p75  = r(p75)
scalar group_p100 = r(max)
restore

gen intensity_high1 = (group <= scalar(group_p100) & group > scalar(group_p75)) if !missing(group)
gen intensity_high2 = (group <= scalar(group_p75)  & group > scalar(group_p50)) if !missing(group)
gen intensity_high3 = (group <= scalar(group_p50)  & group > scalar(group_p25)) if !missing(group)
gen intensity_high4 = (group <= scalar(group_p25)) if !missing(group)
gen intensity_high5 = (group > scalar(group_p50)) if !missing(group)
gen intensity_high6 = (group <= scalar(group_p50)) if !missing(group)

* 创建结果存储矩阵（现在有6个因变量，包括Total碳排和5个分项）
matrix results = J(7, 7, .)  // 7行：6个因变量 + 1行样本量
matrix rownames results = "Total碳排" "Aviation碳排" "Ground Transport碳排" "Industry碳排" "Power碳排" "Residential碳排" "样本数"
matrix colnames results = "全样本" "100-75分位数" "75-50分位数" "50-25分位数" "25-0分位数" "100-50分位数" "50-0分位数"

* 创建标准误存储矩阵
matrix se_results = J(6, 7, .)  // 6行：6个因变量
matrix rownames se_results = "Total碳排" "Aviation碳排值" "Ground Transport碳排" "Industry碳排" "Power碳排" "Residential碳排"
matrix colnames se_results = "全样本" "100-75分位数" "75-50分位数" "50-25分位数" "25-0分位数" "100-50分位数" "50-0分位数"

* 创建样本量存储矩阵
matrix N_results = J(7, 1, .)  // 存储每个分位数组的样本量
matrix rownames N_results = "全样本" "100-75分位数" "75-50分位数" "50-25分位数" "25-0分位数" "100-50分位数" "50-0分位数"

* 计算各分位数组的样本量
quietly count if !missing(y, did, 工业结构, 城市化水平, 人口密度, 技术进步, 财政自给率, 生产总值)
matrix N_results[1, 1] = r(N)

quietly count if intensity_high1 == 1 & !missing(y, did, 工业结构, 城市化水平, 人口密度, 技术进步, 财政自给率, 生产总值)
matrix N_results[2, 1] = r(N)

quietly count if intensity_high2 == 1 & !missing(y, did, 工业结构, 城市化水平, 人口密度, 技术进步, 财政自给率, 生产总值)
matrix N_results[3, 1] = r(N)

quietly count if intensity_high3 == 1 & !missing(y, did, 工业结构, 城市化水平, 人口密度, 技术进步, 财政自给率, 生产总值)
matrix N_results[4, 1] = r(N)

quietly count if intensity_high4 == 1 & !missing(y, did, 工业结构, 城市化水平, 人口密度, 技术进步, 财政自给率, 生产总值)
matrix N_results[5, 1] = r(N)

quietly count if intensity_high5 == 1 & !missing(y, did, 工业结构, 城市化水平, 人口密度, 技术进步, 财政自给率, 生产总值)
matrix N_results[6, 1] = r(N)

quietly count if intensity_high6 == 1 & !missing(y, did, 工业结构, 城市化水平, 人口密度, 技术进步, 财政自给率, 生产总值)
matrix N_results[7, 1] = r(N)

* 循环运行所有回归并存储结果（现在有6个因变量：i=0到5）
* 注意：本版本在所有回归中同时加入 post；结果矩阵仍只提取 did 的系数与标准误
forval i = 0/5 {
    local row = `i' + 1
    
    forval j = 1/7 {
        if `j' == 1 {
            // 全样本回归
            if `i' == 0 {
                capture reghdfe y did post 工业结构 城市化水平 人口密度 技术进步 财政自给率 生产总值, absorb(id day) vce(cluster id)
            }
            else {
                capture reghdfe y`i' did post 工业结构 城市化水平 人口密度 技术进步 财政自给率 生产总值, absorb(id day) vce(cluster id)
            }
        }
        else if `j' == 2 {
            // 100-75分位数
            if `i' == 0 {
                capture reghdfe y did post 工业结构 城市化水平 人口密度 技术进步 财政自给率 生产总值 if intensity_high1 == 1, absorb(id day) vce(cluster id)
            }
            else {
                capture reghdfe y`i' did post 工业结构 城市化水平 人口密度 技术进步 财政自给率 生产总值 if intensity_high1 == 1, absorb(id day) vce(cluster id)
            }
        }
        else if `j' == 3 {
            // 75-50分位数
            if `i' == 0 {
                capture reghdfe y did post 工业结构 城市化水平 人口密度 技术进步 财政自给率 生产总值 if intensity_high2 == 1, absorb(id day) vce(cluster id)
            }
            else {
                capture reghdfe y`i' did post 工业结构 城市化水平 人口密度 技术进步 财政自给率 生产总值 if intensity_high2 == 1, absorb(id day) vce(cluster id)
            }
        }
        else if `j' == 4 {
            // 50-25分位数
            if `i' == 0 {
                capture reghdfe y did post 工业结构 城市化水平 人口密度 技术进步 财政自给率 生产总值 if intensity_high3 == 1, absorb(id day) vce(cluster id)
            }
            else {
                capture reghdfe y`i' did post 工业结构 城市化水平 人口密度 技术进步 财政自给率 生产总值 if intensity_high3 == 1, absorb(id day) vce(cluster id)
            }
        }
        else if `j' == 5 {
            // 25-0分位数
            if `i' == 0 {
                capture reghdfe y did post 工业结构 城市化水平 人口密度 技术进步 财政自给率 生产总值 if intensity_high4 == 1, absorb(id day) vce(cluster id)
            }
            else {
                capture reghdfe y`i' did post 工业结构 城市化水平 人口密度 技术进步 财政自给率 生产总值 if intensity_high4 == 1, absorb(id day) vce(cluster id)
            }
        }
        else if `j' == 6 {
            // 100-50分位数
            if `i' == 0 {
                capture reghdfe y did post 工业结构 城市化水平 人口密度 技术进步 财政自给率 生产总值 if intensity_high5 == 1, absorb(id day) vce(cluster id)
            }
            else {
                capture reghdfe y`i' did post 工业结构 城市化水平 人口密度 技术进步 财政自给率 生产总值 if intensity_high5 == 1, absorb(id day) vce(cluster id)
            }
        }
        else if `j' == 7 {
            // 50-0分位数
            if `i' == 0 {
                capture reghdfe y did post 工业结构 城市化水平 人口密度 技术进步 财政自给率 生产总值 if intensity_high6 == 1, absorb(id day) vce(cluster id)
            }
            else {
                capture reghdfe y`i' did post 工业结构 城市化水平 人口密度 技术进步 财政自给率 生产总值 if intensity_high6 == 1, absorb(id day) vce(cluster id)
            }
        }
        
        // 存储系数和标准误
        if _rc == 0 {
            matrix results[`row', `j'] = _b[did]
            // 注意：标准误矩阵只有6行，不包括样本数行
            if `i' < 6 {
                matrix se_results[`row', `j'] = _se[did]
            }
        }
        else {
            matrix results[`row', `j'] = .
            if `i' < 6 {
                matrix se_results[`row', `j'] = .
            }
        }
    }
}

* 将样本量添加到结果矩阵的最后一行
forval j = 1/7 {
    matrix results[7, `j'] = N_results[`j', 1]
}

* 显示矩阵检查
matrix list results

* 创建输出表格
preserve
clear
set obs 7

* 创建变量名
gen 碳排放类型 = ""
forval i = 1/7 {
    local name : word `i' of "Total碳排" "Aviation碳排值" "Ground Transport碳排" "Industry碳排" "Power碳排" "Residential碳排" "样本数"
    replace 碳排放类型 = "`name'" in `i'
}

* 添加系数显示（带星号）
gen 全样本 = ""
gen 分位数100_75 = ""
gen 分位数75_50 = ""
gen 分位数50_25 = ""
gen 分位数25_0 = ""
gen 分位数100_50 = ""
gen 分位数50_0 = ""

forval i = 1/7 {
    forval j = 1/7 {
        local coef = results[`i', `j']
        
        if `coef' != . {
            // 对于样本数行，直接显示数字
            if `i' == 7 {
                local display_value = string(`coef', "%9.0f")
            }
            // 对于系数行，显示系数和星号
            else {
                local se = se_results[`i', `j']
                if `se' != . {
                    local t = abs(`coef'/`se')
                    local star = ""
                    if `t' > 2.58 local star = "***"
                    else if `t' > 1.96 local star = "**" 
                    else if `t' > 1.65 local star = "*"
                    
                    local display_value = string(`coef', "%9.3f") + "`star'"
                }
                else {
                    local display_value = ""
                }
            }
        }
        else {
            local display_value = ""
        }
        
        if `j' == 1 {
            replace 全样本 = "`display_value'" in `i'
        }
        else if `j' == 2 {
            replace 分位数100_75 = "`display_value'" in `i'
        }
        else if `j' == 3 {
            replace 分位数75_50 = "`display_value'" in `i'
        }
        else if `j' == 4 {
            replace 分位数50_25 = "`display_value'" in `i'
        }
        else if `j' == 5 {
            replace 分位数25_0 = "`display_value'" in `i'
        }
        else if `j' == 6 {
            replace 分位数100_50 = "`display_value'" in `i'
        }
        else if `j' == 7 {
            replace 分位数50_0 = "`display_value'" in `i'
        }
    }
}

* ============================================================
* 输出文件名自动标识 intensity 和分组变量
* 例如：
* 分位数回归结果-日度_intensity-SA_att_grouping-group_base_ci.xlsx
* ============================================================
local output_file "分位数回归结果-日度_with-post_intensity-`intensity_name'_grouping-`grouping_var'.xlsx"

* 导出到Excel
export excel using "`output_file'", firstrow(variables) replace

* 显示实际输出文件名
display "输出文件：`output_file'"

* 显示结果
list
restore