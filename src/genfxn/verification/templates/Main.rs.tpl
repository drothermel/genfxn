#![allow(dead_code)]
$function_code

fn parse_i64_vec(raw: &str) -> Vec<i64> {
    if raw.is_empty() {
        return Vec::new();
    }
    raw.split(',')
        .map(|part| part.parse::<i64>().unwrap())
        .collect()
}

fn parse_intervals(raw: &str) -> Vec<(i64, i64)> {
    if raw.is_empty() {
        return Vec::new();
    }
    raw.split(',')
        .map(|part| {
            let mut iter = part.splitn(2, ':');
            let a = iter.next().unwrap().parse::<i64>().unwrap();
            let b = iter.next().unwrap().parse::<i64>().unwrap();
            (a, b)
        })
        .collect()
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
$main_body
}
