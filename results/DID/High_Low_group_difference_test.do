*******************************************************
* High vs Low 组间系数差异检验
*
* 目的：
*   对三个政策前分组标准，正式检验：
*       beta_High - beta_Low = 0
*
* 三个分组标准：
*   1. Pre-Policy Carbon Intensity
*   2. Pre-Policy Power Emission Share
*   3. Pre-Policy Secondary-Industry Share
*
* 四个文本指标：
*   SA_att
*   AS_att
*   SA_outweight
*   AS_outweight
*
* 六个碳排放结果：
*   Total / Aviation / Ground Transport / Industry / Power / Residential
*
* 统计逻辑：
*   - 高、低组在同一个联合回归中估计
*   - 高、低组分别拥有独立的 did、post、控制变量系数
*   - 高、低组分别拥有独立的时间固定效应
*   - 地区固定效应仍按 id 吸收
*   - 按省份 id 聚类标准误
*   - lincom 直接检验 beta_High - beta_Low = 0
*
* 结果解释：
*   diff_High_Low < 0 且显著：
*       高组系数显著更小/更负，即高组减排关联更强
*   diff_High_Low > 0 且显著：
*       高组系数显著更大/更正，即高组减排关联更弱
*   p >= 0.10：
*       高低组差异在传统显著性水平下不显著
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
* 2. 因变量与控制变量
*******************************************************
gen y_total       = Total碳排值
gen y_aviation    = Aviation碳排值
gen y_transport   = GroundTransport碳排值
gen y_industry    = Industry碳排值
gen y_power       = Power碳排值
gen y_residential = Residential碳排值

local outcomes "y_total y_aviation y_transport y_industry y_power y_residential"
local controls "工业结构 城市化水平 人口密度 技术进步 财政自给率 生产总值"
local measures "SA_att AS_att SA_outweight AS_outweight"

*******************************************************
* 3. 构造三个政策前分组变量
* daily   ：政策前30天均值（与现有日度结果保持一致）
* monthly ：政策前一期（月）（与现有月度结果保持一致）
*******************************************************

if "`freq'" == "daily" {
    gen byte __pre_base = (policy_group > 0 & day >= policy_group - 30 & day < policy_group)
}
else if "`freq'" == "monthly" {
    gen byte __pre_base = (policy_group > 0 & month == policy_group - 1)
}

* 3.1 Pre-Policy Carbon Intensity
capture confirm variable 碳排强度
if _rc == 0 {
    gen double __carbon_intensity = 碳排强度
}
else {
    gen double __carbon_intensity = Total碳排值 / 生产总值 ///
        if !missing(Total碳排值, 生产总值) & 生产总值 != 0
}
bysort id: egen group_base_ci = mean(cond(__pre_base == 1, __carbon_intensity, .))

* 3.2 Pre-Policy Power Emission Share
gen double __power_share = Power碳排值 / Total碳排值 ///
    if !missing(Power碳排值, Total碳排值) & Total碳排值 != 0
bysort id: egen group_base_power_share = mean(cond(__pre_base == 1, __power_share, .))

* 3.3 Pre-Policy Secondary-Industry Share
bysort id: egen group_base_industry2 = mean(cond(__pre_base == 1, 工业结构, .))

* 每个地区只参与一次中位数计算
egen byte __idtag = tag(id)

local grouping_vars "group_base_ci group_base_power_share group_base_industry2"

*******************************************************
* 4. 建立结果存储文件
*******************************************************
tempfile diff_results
tempname H

postfile `H' ///
    str10 frequency ///
    str32 grouping_var ///
    str42 grouping_label ///
    str24 outcome ///
    str24 measure ///
    double beta_high beta_low diff_High_Low se_diff t_diff p_diff lb95 ub95 ///
    double N_high N_low clusters_high clusters_low N_total N_clusters ///
    str3 stars ///
    str48 direction ///
    using `diff_results', replace

*******************************************************
* 5. 循环：3 个分组变量
*******************************************************
foreach gvar of local grouping_vars {

    quietly summarize `gvar' if __idtag == 1 & !missing(`gvar'), detail
    local p50 = r(p50)

    if "`gvar'" == "group_base_ci" {
        local grouping_label "Pre-Policy Carbon Intensity"
    }
    else if "`gvar'" == "group_base_power_share" {
        local grouping_label "Pre-Policy Power Emission Share"
    }
    else if "`gvar'" == "group_base_industry2" {
        local grouping_label "Pre-Policy Secondary-Industry Share"
    }

    display as text "============================================================"
    display as text "Grouping: `grouping_label'"
    display as text "Median = `p50'"

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

        ***************************************************
        * 4 个文本指标
        ***************************************************
        foreach mvar of local measures {

            preserve

            * 仅保留当前分组变量非缺失的地区
            keep if !missing(`gvar')

            * 高/低组：高组 > 中位数；低组 <= 中位数
            gen byte __high = (`gvar' > `p50')

            * 当前文本指标 × post
            gen double __did = `mvar' * post

            ************************************************
            * 分组样本量与 cluster 数
            ************************************************
            quietly count if __high == 1 & !missing(`yvar', __did, post, ///
                工业结构, 城市化水平, 人口密度, 技术进步, 财政自给率, 生产总值)
            local NH = r(N)

            quietly count if __high == 0 & !missing(`yvar', __did, post, ///
                工业结构, 城市化水平, 人口密度, 技术进步, 财政自给率, 生产总值)
            local NL = r(N)

            egen byte __tag_high = tag(id) if __high == 1
            quietly count if __tag_high == 1
            local CH = r(N)

            egen byte __tag_low = tag(id) if __high == 0
            quietly count if __tag_low == 1
            local CL = r(N)

            ************************************************
            * 高低组分别拥有自己的 DID 系数
            ************************************************
            gen double did_high = 0
            replace did_high = __did if __high == 1

            gen double did_low = 0
            replace did_low = __did if __high == 0

            ************************************************
            * 高低组分别拥有自己的 post 系数
            ************************************************
            gen double post_high = 0
            replace post_high = post if __high == 1

            gen double post_low = 0
            replace post_low = post if __high == 0

            ************************************************
            * 高低组分别拥有自己的控制变量系数
            * 这样更接近原先把高、低组分开回归的设定
            ************************************************
            gen double c1_high = 0
            gen double c1_low  = 0
            replace c1_high = 工业结构 if __high == 1
            replace c1_low  = 工业结构 if __high == 0

            gen double c2_high = 0
            gen double c2_low  = 0
            replace c2_high = 城市化水平 if __high == 1
            replace c2_low  = 城市化水平 if __high == 0

            gen double c3_high = 0
            gen double c3_low  = 0
            replace c3_high = 人口密度 if __high == 1
            replace c3_low  = 人口密度 if __high == 0

            gen double c4_high = 0
            gen double c4_low  = 0
            replace c4_high = 技术进步 if __high == 1
            replace c4_low  = 技术进步 if __high == 0

            gen double c5_high = 0
            gen double c5_low  = 0
            replace c5_high = 财政自给率 if __high == 1
            replace c5_low  = 财政自给率 if __high == 0

            gen double c6_high = 0
            gen double c6_low  = 0
            replace c6_high = 生产总值 if __high == 1
            replace c6_low  = 生产总值 if __high == 0

            ************************************************
            * 高低组分别拥有自己的时间固定效应
            * 地区 id 本身已经只属于某一个组，因此 absorb(id ...) 即可
            ************************************************
            egen long __group_time = group(__high `timevar')

            ************************************************
            * 联合回归
            ************************************************
            capture quietly reghdfe `yvar' ///
                did_high did_low ///
                post_high post_low ///
                c1_high c1_low ///
                c2_high c2_low ///
                c3_high c3_low ///
                c4_high c4_low ///
                c5_high c5_low ///
                c6_high c6_low, ///
                absorb(id __group_time) vce(cluster id)

            if _rc == 0 {
                local bH = _b[did_high]
                local bL = _b[did_low]
                local NT = e(N)
                local NC = e(N_clust)

                ************************************************
                * 正式检验：beta_High - beta_Low = 0
                ************************************************
                capture quietly lincom did_high - did_low

                if _rc == 0 {
                    local d   = r(estimate)
                    local sed = r(se)
                    local tt  = `d'/`sed'
                    local pp  = r(p)
                    local lb  = r(lb)
                    local ub  = r(ub)

                    * 星号依据 lincom 双侧 p 值
                    local star ""
                    if `pp' < 0.01 local star "***"
                    else if `pp' < 0.05 local star "**"
                    else if `pp' < 0.10 local star "*"

                    * diff = High - Low
                    * 对碳排放而言，diff<0 表示高组系数更负、减排关联更强
                    local dir "No significant difference"

                    if `d' < 0 & `pp' < 0.01 local dir "High < Low: more negative (1%)"
                    else if `d' < 0 & `pp' < 0.05 local dir "High < Low: more negative (5%)"
                    else if `d' < 0 & `pp' < 0.10 local dir "High < Low: more negative (10%)"
                    else if `d' > 0 & `pp' < 0.01 local dir "High > Low: less negative (1%)"
                    else if `d' > 0 & `pp' < 0.05 local dir "High > Low: less negative (5%)"
                    else if `d' > 0 & `pp' < 0.10 local dir "High > Low: less negative (10%)"

                    post `H' ///
                        ("`freq'") ///
                        ("`gvar'") ///
                        ("`grouping_label'") ///
                        ("`ylabel'") ///
                        ("`mvar'") ///
                        (`bH') (`bL') ///
                        (`d') (`sed') (`tt') (`pp') (`lb') (`ub') ///
                        (`NH') (`NL') (`CH') (`CL') (`NT') (`NC') ///
                        ("`star'") ("`dir'")
                }
            }

            restore
        }
    }
}

postclose `H'

*******************************************************
* 6. 整理结果
*******************************************************
use `diff_results', clear

gen str20 diff_display = string(diff_High_Low, "%9.3f") + stars

order frequency grouping_label grouping_var outcome measure ///
      beta_high beta_low diff_High_Low diff_display ///
      se_diff t_diff p_diff lb95 ub95 direction stars ///
      N_high N_low clusters_high clusters_low N_total N_clusters

format beta_high beta_low diff_High_Low se_diff t_diff lb95 ub95 %9.4f
format p_diff %9.4f
format N_high N_low clusters_high clusters_low N_total N_clusters %9.0f

sort grouping_var measure outcome

*******************************************************
* 7. 屏幕查看
*******************************************************
list grouping_label outcome measure ///
     beta_high beta_low diff_display p_diff direction ///
     clusters_high clusters_low, ///
     sepby(grouping_label measure) noobs

*******************************************************
* 8. 导出完整结果
*******************************************************
local outfile "High_vs_Low_group_difference_test_`freq'.xlsx"
export excel using "`outfile'", firstrow(variables) replace

display as result "组间差异检验结果已输出：`outfile'"

*******************************************************
* 结果解释
*
* diff_High_Low = beta_high - beta_low
*
* diff < 0 且 p<0.10/0.05/0.01：
*   高组系数显著小于低组
*   对碳排放而言，即高组负向/减排关联显著更强
*
* diff > 0 且 p<0.10/0.05/0.01：
*   高组系数显著大于低组
*   对碳排放而言，即高组负向/减排关联显著更弱
*
* p >= 0.10：
*   高低组系数差异在传统显著性水平下不显著
*******************************************************
