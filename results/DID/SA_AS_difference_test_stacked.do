*******************************************************
* S-to-A vs A-to-S 系数差异检验（推荐：stacked equations）
*
* 比较：
*   Pair 1: SA_att       vs AS_att
*   Pair 2: SA_outweight vs AS_outweight
*
* 覆盖：
*   - 6 个碳排放结果
*   - 3 个政策前分组变量
*   - 全样本 + 四分位组 + 高/低二分组
*
* 统计逻辑：
*   - SA 与 AS 仍对应“各自单独回归”的系数含义
*   - 将两条方程堆叠在同一数据中
*   - 每条方程拥有独立的 post、控制变量、地区FE和时间FE
*   - 按原始省份 id 聚类，使两条方程的估计误差允许相关
*   - lincom 直接检验 beta_SA - beta_AS = 0
*
* 输出：
*   beta_SA、beta_AS、SA-AS差值、差值SE、t、p、95%CI、
*   星号、方向判断、两边样本量、cluster数
*******************************************************

clear all
set more off

cd "D:\桌面\sim-degree3.0\results\DID"
sysdir set PLUS "D:\Stata17\ado\plus"

* 如未安装：
* ssc install reghdfe, replace
* ssc install ftools, replace

*******************************************************
* 0. 选择频率：daily 或 monthly
*******************************************************
local freq "daily"
* local freq "monthly"

if "`freq'" == "daily" {
    import excel "日度_ceads.xlsx", firstrow clear
    local timevar day
    local policyvar policy_day
}
else if "`freq'" == "monthly" {
    import excel "月度_ceads.xlsx", firstrow clear
    local timevar month
    local policyvar policy_month
}
else {
    display as error "freq 只能是 daily 或 monthly"
    exit 198
}

*******************************************************
* 1. 样本与 post
*******************************************************
keep if treated != 0 & !missing(treated)

gen policy_group = `policyvar'
gen byte post = (`timevar' >= policy_group) if !missing(policy_group)
replace post = 0 if missing(post)

*******************************************************
* 2. 四个文本度量 × post
*******************************************************
gen did_SA_att       = SA_att       * post
gen did_AS_att       = AS_att       * post
gen did_SA_outweight = SA_outweight * post
gen did_AS_outweight = AS_outweight * post

*******************************************************
* 3. 因变量与控制变量
*******************************************************
gen y_total       = Total碳排值
gen y_aviation    = Aviation碳排值
gen y_transport   = GroundTransport碳排值
gen y_industry    = Industry碳排值
gen y_power       = Power碳排值
gen y_residential = Residential碳排值

local outcomes "y_total y_aviation y_transport y_industry y_power y_residential"
local controls "工业结构 城市化水平 人口密度 技术进步 财政自给率 生产总值"

*******************************************************
* 4. 三个政策前分组变量
* daily   ：政策前30天均值（与现有日度结果保持一致）
* monthly ：政策前一期（月）（与现有月度结果保持一致）
*******************************************************

if "`freq'" == "daily" {
    gen byte __pre_base = (policy_group > 0 & day >= policy_group - 30 & day < policy_group)
}
else if "`freq'" == "monthly" {
    gen byte __pre_base = (policy_group > 0 & month == policy_group - 1)
}

* 4.1 Pre-Policy Carbon Intensity
capture confirm variable 碳排强度
if _rc == 0 {
    gen double __carbon_intensity = 碳排强度
}
else {
    gen double __carbon_intensity = Total碳排值 / 生产总值 ///
        if !missing(Total碳排值, 生产总值) & 生产总值 != 0
}
bysort id: egen group_base_ci = mean(cond(__pre_base == 1, __carbon_intensity, .))

* 4.2 Pre-Policy Power Emission Share
gen double __power_share = Power碳排值 / Total碳排值 ///
    if !missing(Power碳排值, Total碳排值) & Total碳排值 != 0
bysort id: egen group_base_power_share = mean(cond(__pre_base == 1, __power_share, .))

* 4.3 Pre-Policy Secondary-Industry Share
bysort id: egen group_base_industry2 = mean(cond(__pre_base == 1, 工业结构, .))

* 每个地区仅参与一次分位点计算
egen byte __idtag = tag(id)

local grouping_vars "group_base_ci group_base_power_share group_base_industry2"

*******************************************************
* 5. 建立结果存储文件
*******************************************************
tempfile diff_results
tempname H

postfile `H' ///
    str10 frequency ///
    str32 grouping_var ///
    str38 grouping_label ///
    str24 group_label ///
    str28 outcome ///
    str30 measure_pair ///
    double beta_SA beta_AS diff_SA_AS se_diff t_diff p_diff lb95 ub95 ///
    double N_SA N_AS N_stacked N_clusters ///
    str3 stars ///
    str40 direction ///
    using `diff_results', replace

*******************************************************
* 6. 循环：3 个分组变量
*******************************************************
foreach gvar of local grouping_vars {

    quietly summarize `gvar' if __idtag == 1 & !missing(`gvar'), detail
    local p25 = r(p25)
    local p50 = r(p50)
    local p75 = r(p75)

    if "`gvar'" == "group_base_ci" {
        local grouping_label "Pre-Policy Carbon Intensity"
    }
    else if "`gvar'" == "group_base_power_share" {
        local grouping_label "Pre-Policy Power Emission Share"
    }
    else if "`gvar'" == "group_base_industry2" {
        local grouping_label "Pre-Policy Secondary-Industry Share"
    }

    display as text "=================================================="
    display as text "Grouping: `grouping_label'"
    display as text "P25=`p25'  P50=`p50'  P75=`p75'"

    ***************************************************
    * 7 个样本范围
    ***************************************************
    forvalues j = 1/7 {

        if `j' == 1 {
            local glabel "Full sample"
        }
        else if `j' == 2 {
            local glabel "100-75 percentile"
        }
        else if `j' == 3 {
            local glabel "75-50 percentile"
        }
        else if `j' == 4 {
            local glabel "50-25 percentile"
        }
        else if `j' == 5 {
            local glabel "25-0 percentile"
        }
        else if `j' == 6 {
            local glabel "High (100-50)"
        }
        else if `j' == 7 {
            local glabel "Low (50-0)"
        }

        ***************************************************
        * 6 个结果变量
        ***************************************************
        foreach yvar of local outcomes {

            if "`yvar'" == "y_total"       local ylabel "Total emissions"
            if "`yvar'" == "y_aviation"    local ylabel "Aviation"
            if "`yvar'" == "y_transport"   local ylabel "Ground Transport"
            if "`yvar'" == "y_industry"    local ylabel "Industry"
            if "`yvar'" == "y_power"       local ylabel "Power"
            if "`yvar'" == "y_residential" local ylabel "Residential"

            ************************************************
            * 两组指标依次比较
            ************************************************
            forvalues pair = 1/2 {

                if `pair' == 1 {
                    local pairlabel "SA_att vs AS_att"
                    local didSA did_SA_att
                    local didAS did_AS_att
                }
                else if `pair' == 2 {
                    local pairlabel "SA_outweight vs AS_outweight"
                    local didSA did_SA_outweight
                    local didAS did_AS_outweight
                }

                preserve

                ********************************************
                * 应用当前分组
                ********************************************
                if `j' == 2 {
                    keep if `gvar' > `p75' & !missing(`gvar')
                }
                else if `j' == 3 {
                    keep if `gvar' > `p50' & `gvar' <= `p75' & !missing(`gvar')
                }
                else if `j' == 4 {
                    keep if `gvar' > `p25' & `gvar' <= `p50' & !missing(`gvar')
                }
                else if `j' == 5 {
                    keep if `gvar' <= `p25' & !missing(`gvar')
                }
                else if `j' == 6 {
                    keep if `gvar' > `p50' & !missing(`gvar')
                }
                else if `j' == 7 {
                    keep if `gvar' <= `p50' & !missing(`gvar')
                }

                ********************************************
                * 记录两条“原始独立回归”各自的有效样本量
                ********************************************
                quietly count if !missing(`yvar', `didSA', post, ///
                    工业结构, 城市化水平, 人口密度, 技术进步, 财政自给率, 生产总值)
                local NSA = r(N)

                quietly count if !missing(`yvar', `didAS', post, ///
                    工业结构, 城市化水平, 人口密度, 技术进步, 财政自给率, 生产总值)
                local NAS = r(N)

                ********************************************
                * STACK 两条方程
                * eq=1：S-to-A 方程
                * eq=2：A-to-S 方程
                ********************************************
                gen long __obs = _n
                expand 2
                bysort __obs: gen byte eq = _n

                * 核心解释变量：每条方程只使用自己的 DID 强度项
                gen double x_SA = 0
                replace x_SA = `didSA' if eq == 1

                gen double x_AS = 0
                replace x_AS = `didAS' if eq == 2

                * post 也允许两条方程拥有独立系数
                gen double post_SA = 0
                replace post_SA = post if eq == 1

                gen double post_AS = 0
                replace post_AS = post if eq == 2

                * 控制变量允许两条方程拥有独立系数
                gen double c1_SA = 0
                gen double c1_AS = 0
                replace c1_SA = 工业结构 if eq == 1
                replace c1_AS = 工业结构 if eq == 2

                gen double c2_SA = 0
                gen double c2_AS = 0
                replace c2_SA = 城市化水平 if eq == 1
                replace c2_AS = 城市化水平 if eq == 2

                gen double c3_SA = 0
                gen double c3_AS = 0
                replace c3_SA = 人口密度 if eq == 1
                replace c3_AS = 人口密度 if eq == 2

                gen double c4_SA = 0
                gen double c4_AS = 0
                replace c4_SA = 技术进步 if eq == 1
                replace c4_AS = 技术进步 if eq == 2

                gen double c5_SA = 0
                gen double c5_AS = 0
                replace c5_SA = 财政自给率 if eq == 1
                replace c5_AS = 财政自给率 if eq == 2

                gen double c6_SA = 0
                gen double c6_AS = 0
                replace c6_SA = 生产总值 if eq == 1
                replace c6_AS = 生产总值 if eq == 2

                * 每条方程分别拥有地区FE和时间FE
                egen long __eq_id   = group(eq id)
                egen long __eq_time = group(eq `timevar')

                ********************************************
                * 堆叠回归
                ********************************************
                capture quietly reghdfe `yvar' ///
                    x_SA x_AS ///
                    post_SA post_AS ///
                    c1_SA c1_AS ///
                    c2_SA c2_AS ///
                    c3_SA c3_AS ///
                    c4_SA c4_AS ///
                    c5_SA c5_AS ///
                    c6_SA c6_AS, ///
                    absorb(__eq_id __eq_time) vce(cluster id)

                if _rc == 0 {
                    local bSA = _b[x_SA]
                    local bAS = _b[x_AS]
                    local NST = e(N)
                    local NC  = e(N_clust)

                    ****************************************
                    * 正式差异检验：beta_SA - beta_AS = 0
                    ****************************************
                    capture quietly lincom x_SA - x_AS

                    if _rc == 0 {
                        local d   = r(estimate)
                        local sed = r(se)
                        local tt  = `d'/`sed'
                        local pp  = r(p)
                        local lb  = r(lb)
                        local ub  = r(ub)

                        * 星号直接依据 lincom 返回的双侧 p 值
                        local star ""
                        if `pp' < 0.01 local star "***"
                        else if `pp' < 0.05 local star "**"
                        else if `pp' < 0.10 local star "*"

                        * 自动判断方向
                        * diff = SA - AS
                        * 对碳排放而言：diff<0 表示 SA 比 AS 更负，即减排关联更强
                        local dir "No significant difference"

                        if `d' < 0 & `pp' < 0.01 local dir "SA < AS: more negative (1%)"
                        else if `d' < 0 & `pp' < 0.05 local dir "SA < AS: more negative (5%)"
                        else if `d' < 0 & `pp' < 0.10 local dir "SA < AS: more negative (10%)"
                        else if `d' > 0 & `pp' < 0.01 local dir "SA > AS: less negative (1%)"
                        else if `d' > 0 & `pp' < 0.05 local dir "SA > AS: less negative (5%)"
                        else if `d' > 0 & `pp' < 0.10 local dir "SA > AS: less negative (10%)"

                        post `H' ///
                            ("`freq'") ///
                            ("`gvar'") ///
                            ("`grouping_label'") ///
                            ("`glabel'") ///
                            ("`ylabel'") ///
                            ("`pairlabel'") ///
                            (`bSA') (`bAS') ///
                            (`d') (`sed') (`tt') (`pp') (`lb') (`ub') ///
                            (`NSA') (`NAS') (`NST') (`NC') ///
                            ("`star'") ("`dir'")
                    }
                }

                restore
            }
        }
    }
}

postclose `H'

*******************************************************
* 7. 整理结果
*******************************************************
use `diff_results', clear

gen str20 diff_display = string(diff_SA_AS, "%9.3f") + stars

order frequency grouping_label grouping_var group_label outcome measure_pair ///
      beta_SA beta_AS diff_SA_AS diff_display se_diff t_diff p_diff lb95 ub95 ///
      direction stars N_SA N_AS N_stacked N_clusters

format beta_SA beta_AS diff_SA_AS se_diff t_diff lb95 ub95 %9.4f
format p_diff %9.4f
format N_SA N_AS N_stacked N_clusters %9.0f

sort grouping_var group_label measure_pair outcome

*******************************************************
* 8. 屏幕查看
*******************************************************
list grouping_label group_label outcome measure_pair ///
     beta_SA beta_AS diff_display p_diff direction N_clusters, ///
     sepby(grouping_label group_label measure_pair) noobs

*******************************************************
* 9. 导出完整结果
*******************************************************
local outfile "SA_vs_AS_difference_test_stacked_`freq'.xlsx"
export excel using "`outfile'", firstrow(variables) replace

display as result "完整差异检验结果已输出：`outfile'"

*******************************************************
* 10. 另导出正文更常用的 全样本 + High + Low
*******************************************************
preserve
keep if inlist(group_label, "Full sample", "High (100-50)", "Low (50-0)")
local outfile_main "SA_vs_AS_difference_test_stacked_`freq'_main.xlsx"
export excel using "`outfile_main'", firstrow(variables) replace
display as result "正文简化结果已输出：`outfile_main'"
restore

*******************************************************
* 结果解释
*
* diff_SA_AS = beta_SA - beta_AS
*
* diff < 0 且 p<0.10/0.05/0.01：
*   S-to-A 系数显著小于 A-to-S
*   对碳排放而言，即 S-to-A 的负向/减排关联显著更强
*
* diff > 0 且 p<0.10/0.05/0.01：
*   S-to-A 系数显著大于 A-to-S
*   对碳排放而言，即 S-to-A 的负向/减排关联显著更弱
*
* p >= 0.10：
*   两个系数差异在传统显著性水平下不显著
*******************************************************
