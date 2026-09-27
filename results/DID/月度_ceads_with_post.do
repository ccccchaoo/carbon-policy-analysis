cd "D:\桌面\sim-degree3.0\results\DID"
sysdir set PLUS "D:\Stata17\ado\plus"

*请选择本地stata环境

*ssc install reghdfe
*ssc install ftools
*ssc install coefplot, replace
*ssc install e
import excel "月度_ceads.xlsx", firstrow clear

keep if treated != 0 & !missing(treated)

* 处理policy_time变量
gen policy_group = policy_month
replace policy_group = 0 if missing(policy_group)

* 生成处理变量
gen post = (month >= policy_group & !missing(policy_group))
replace post = 0 if missing(policy_group)

*分位数指标	SA_att	AS_att	SA_outweight	AS_outweight
gen intensity = AS_outweight

* 生成DID交乘项treated/degree
gen did = intensity * post


///*
gen y1 = Aviation碳排值
gen y2 = GroundTransport碳排值
gen y3 = Industry碳排值
gen y4 = Power碳排值
gen y5 = Residential碳排值
gen y = Total碳排值
//*/



* ============================================================
* 异质性分组：按各地区政策发生前一期（月）的基期状态分组
* 注意：intensity = AS_outweight 仍仅用于构造 did，不再作为分组依据
* ============================================================

* 标记政策发生前一期（月）
gen __base_prev = (policy_group > 0 & month == policy_group - 1)

* 1. 基期前一期总碳排量
bysort id: egen group_base_total = max(cond(__base_prev == 1, Total碳排值, .))

* 2. 基期前一期碳排强度
* 若原始数据已有“碳排强度”，直接使用；否则按 Total碳排值 / 生产总值 构造
capture confirm variable 碳排强度
if !_rc {
    bysort id: egen group_base_ci = max(cond(__base_prev == 1, 碳排强度, .))
}
else {
    gen __carbon_intensity = Total碳排值 / 生产总值 if !missing(Total碳排值, 生产总值) & 生产总值 != 0
    bysort id: egen group_base_ci = max(cond(__base_prev == 1, __carbon_intensity, .))
}

* 3. 基期前一期电力碳排占总碳排比重
gen __power_share = Power碳排值 / Total碳排值 if !missing(Power碳排值, Total碳排值) & Total碳排值 != 0
bysort id: egen group_base_power_share = max(cond(__base_prev == 1, __power_share, .))

* 4. 基期前一期第二产业占比
* 这里沿用原程序中的“工业结构”作为第二产业占比指标
bysort id: egen group_base_industry2 = max(cond(__base_prev == 1, 工业结构, .))

* ------------------------------------------------------------
* 在这里切换异质性分组变量：一次启用一个即可
* ------------------------------------------------------------
local grouping_var group_base_total
* local grouping_var group_base_ci
* local grouping_var group_base_power_share
* local grouping_var group_base_industry2

* 每个地区只参与一次分位点计算，避免月度观测重复赋权
egen __idtag = tag(id)
quietly summarize `grouping_var' if __idtag == 1 & !missing(`grouping_var'), detail
local p25 = r(p25)
local p50 = r(p50)
local p75 = r(p75)

* 按基期状态生成四分位组及高/低二分组
* 保留原变量名 intensity_high1-intensity_high6，确保后续代码无需改动
gen intensity_high1 = (`grouping_var' >  `p75') if !missing(`grouping_var')
gen intensity_high2 = (`grouping_var' >  `p50' & `grouping_var' <= `p75') if !missing(`grouping_var')
gen intensity_high3 = (`grouping_var' >  `p25' & `grouping_var' <= `p50') if !missing(`grouping_var')
gen intensity_high4 = (`grouping_var' <= `p25') if !missing(`grouping_var')
gen intensity_high5 = (`grouping_var' >  `p50') if !missing(`grouping_var')
gen intensity_high6 = (`grouping_var' <= `p50') if !missing(`grouping_var')

* 检查基期变量覆盖情况与分位点
display "当前分组变量: `grouping_var'"
display "P25 = `p25', P50 = `p50', P75 = `p75'"
count if __idtag == 1 & missing(`grouping_var')
display "缺少政策前一期基期值的地区数 = " r(N)

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
forval i = 0/5 {
    local row = `i' + 1
    
    forval j = 1/7 {
        if `j' == 1 {
            // 全样本回归
            if `i' == 0 {
                capture reghdfe y did post 工业结构 城市化水平 人口密度 技术进步 财政自给率 生产总值, absorb(id month) vce(cluster id)
            }
            else {
                capture reghdfe y`i' did post 工业结构 城市化水平 人口密度 技术进步 财政自给率 生产总值, absorb(id month) vce(cluster id)
            }
        }
        else if `j' == 2 {
            // 100-75分位数
            if `i' == 0 {
                capture reghdfe y did post 工业结构 城市化水平 人口密度 技术进步 财政自给率 生产总值 if intensity_high1 == 1, absorb(id month) vce(cluster id)
            }
            else {
                capture reghdfe y`i' did post 工业结构 城市化水平 人口密度 技术进步 财政自给率 生产总值 if intensity_high1 == 1, absorb(id month) vce(cluster id)
            }
        }
        else if `j' == 3 {
            // 75-50分位数
            if `i' == 0 {
                capture reghdfe y did post 工业结构 城市化水平 人口密度 技术进步 财政自给率 生产总值 if intensity_high2 == 1, absorb(id month) vce(cluster id)
            }
            else {
                capture reghdfe y`i' did post 工业结构 城市化水平 人口密度 技术进步 财政自给率 生产总值 if intensity_high2 == 1, absorb(id month) vce(cluster id)
            }
        }
        else if `j' == 4 {
            // 50-25分位数
            if `i' == 0 {
                capture reghdfe y did post 工业结构 城市化水平 人口密度 技术进步 财政自给率 生产总值 if intensity_high3 == 1, absorb(id month) vce(cluster id)
            }
            else {
                capture reghdfe y`i' did post 工业结构 城市化水平 人口密度 技术进步 财政自给率 生产总值 if intensity_high3 == 1, absorb(id month) vce(cluster id)
            }
        }
        else if `j' == 5 {
            // 25-0分位数
            if `i' == 0 {
                capture reghdfe y did post 工业结构 城市化水平 人口密度 技术进步 财政自给率 生产总值 if intensity_high4 == 1, absorb(id month) vce(cluster id)
            }
            else {
                capture reghdfe y`i' did post 工业结构 城市化水平 人口密度 技术进步 财政自给率 生产总值 if intensity_high4 == 1, absorb(id month) vce(cluster id)
            }
        }
        else if `j' == 6 {
            // 100-50分位数
            if `i' == 0 {
                capture reghdfe y did post 工业结构 城市化水平 人口密度 技术进步 财政自给率 生产总值 if intensity_high5 == 1, absorb(id month) vce(cluster id)
            }
            else {
                capture reghdfe y`i' did post 工业结构 城市化水平 人口密度 技术进步 财政自给率 生产总值 if intensity_high5 == 1, absorb(id month) vce(cluster id)
            }
        }
        else if `j' == 7 {
            // 50-0分位数
            if `i' == 0 {
                capture reghdfe y did post 工业结构 城市化水平 人口密度 技术进步 财政自给率 生产总值 if intensity_high6 == 1, absorb(id month) vce(cluster id)
            }
            else {
                capture reghdfe y`i' did post 工业结构 城市化水平 人口密度 技术进步 财政自给率 生产总值 if intensity_high6 == 1, absorb(id month) vce(cluster id)
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

* 导出到Excel
export excel using "分位数回归结果-月度_with-post.xlsx", firstrow(variables) replace

* 显示结果
list
restore