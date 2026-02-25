#![allow(dead_code)]
$function_code

fn parse_i64_vec(raw: &str) -> Vec<i64> {
    if raw.is_empty() {
        return Vec::new();
    }
    raw.split(',')
        .map(|part| {
            part.parse::<i64>().expect(
                &format!("invalid i64 token '{part}' while parsing '{raw}'"),
            )
        })
        .collect()
}

fn parse_intervals(raw: &str) -> Vec<(i64, i64)> {
    if raw.is_empty() {
        return Vec::new();
    }
    raw.split(',')
        .map(|part| {
            let mut iter = part.splitn(2, ':');
            let a_str = iter.next().expect(
                &format!("missing interval start in '{part}' (expected start:end)"),
            );
            let b_str = iter.next().expect(
                &format!("missing interval end in '{part}' (expected start:end)"),
            );
            let a = a_str.parse::<i64>().expect(
                &format!("invalid interval start '{a_str}' in '{part}'"),
            );
            let b = b_str.parse::<i64>().expect(
                &format!("invalid interval end '{b_str}' in '{part}'"),
            );
            (a, b)
        })
        .collect()
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
$main_body
}
